import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

# llm = init_chat_model(model="llama-3.3-70b-versatile", model_provider="groq", temperature=0)
llm = init_chat_model(model="gemini-2.5-flash", model_provider="google-genai", temperature=0)

stdio_client_params = StdioServerParameters(
    command="uvx",
    args=["--from", "d365fo-client", "d365fo-mcp-server"],
    env={
        "D365FO_BASE_URL": os.getenv("D365FO_BASE_URL"),
        "D365FO_CLIENT_ID": os.getenv("D365FO_CLIENT_ID"),
        "D365FO_CLIENT_SECRET": os.getenv("D365FO_CLIENT_SECRET"),
        "D365FO_TENANT_ID": os.getenv("D365FO_TENANT_ID"),
    }
)

# -----------------------------------------------------------
# 1. Pydantic Models
# -----------------------------------------------------------

class PurchaseOrderLine(BaseModel):
    line_number: str | None = None
    item_id: str | None = None
    item_name: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    total_amount: float | None = None
    delivery_date: str | None = None

class PurchaseOrder(BaseModel):
    po_number: str | None = None
    vendor_id: str | None = None
    vendor_name: str | None = None
    status: str | None = None
    order_date: str | None = None
    total_amount: float | None = None
    currency: str | None = None
    lines: list[PurchaseOrderLine] = []


# -----------------------------------------------------------
# 2. Graph State
# -----------------------------------------------------------

class AgentState(MessagesState):
    structured_output: PurchaseOrder | None = None
    po_number: str | None = None


# -----------------------------------------------------------
# 3. Build Graph
# -----------------------------------------------------------

def build_graph(tools: list):

    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    # Node 1 — LLM decides what tools to call
    def llm_node(state: AgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    # Node 2 — Format into Pydantic class
    def formatter_node(state: AgentState) -> dict:
        # Collect ALL tool responses from message history
        all_tool_data = []
        for msg in state["messages"]:
            if hasattr(msg, "content") and hasattr(msg, "name"):
                all_tool_data.append(f"[{msg.name}]:\n{msg.content}")

        combined = "\n\n".join(all_tool_data)

        formatting_llm = llm.with_structured_output(PurchaseOrder)
        structured = formatting_llm.invoke([
            HumanMessage(content=f"""
                Extract ALL purchase order details including header AND line items
                from the data below. Make sure to populate the lines array
                with every line item found.

                Data:
                {combined}
            """)
        ])
        return {"structured_output": structured}

    # Routing
    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "formatter"

    graph = StateGraph(AgentState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_node("formatter", formatter_node)

    graph.add_edge(START, "llm")
    graph.add_conditional_edges("llm", should_continue, {
        "tools": "tools",
        "formatter": "formatter"
    })
    graph.add_edge("tools", "llm")
    graph.add_edge("formatter", END)

    return graph.compile()


# -----------------------------------------------------------
# 4. Main — properly close aiohttp session
# -----------------------------------------------------------

async def main():
    # ✅ Fix unclosed session — use try/finally to ensure cleanup
    try:
        async with stdio_client(stdio_client_params) as (read, write):
            async with ClientSession(read_stream=read, write_stream=write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                print(f"✅ {len(tools)} tools loaded\n")

                graph = build_graph(tools)

                # ✅ Explicitly ask for header AND lines in one prompt
                result = await graph.ainvoke({
                    "messages": [HumanMessage(content="""
                        For purchase order number '000011':
                        1. Get the purchase order header details
                        2. Get all the purchase order LINE ITEMS
                        Return everything you find.
                    """)],
                    "structured_output": None,
                    "po_number": "000011"
                })

                po: PurchaseOrder = result["structured_output"]

                print("===== PURCHASE ORDER =====")
                print(f"PO Number  : {po.po_number}")
                print(f"Vendor     : {po.vendor_name} ({po.vendor_id})")
                print(f"Status     : {po.status}")
                print(f"Order Date : {po.order_date}")
                print(f"Total      : {po.total_amount} {po.currency}")

                if po.lines:
                    print(f"\n--- Line Items ({len(po.lines)}) ---")
                    for line in po.lines:
                        print(f"  [{line.line_number}] {line.item_name}")
                        print(f"    Item ID : {line.item_id}")
                        print(f"    Qty     : {line.quantity}")
                        print(f"    Price   : {line.unit_price}")
                        print(f"    Total   : {line.total_amount}")
                        print(f"    Deliver : {line.delivery_date}")
                else:
                    print("\n⚠️  No line items returned.")
                    print("    Check if the MCP tool for PO lines is named differently:")
                    for t in tools:
                        if "purchase" in t.name.lower() or "line" in t.name.lower():
                            print(f"    → {t.name}: {t.description}")

    finally:
        # ✅ Give event loop a moment to close lingering aiohttp connections
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())