import asyncio
import os
from typing import Any,List, Literal
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from mcp import ClientSession, StdioServerParameters, stdio_client
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage,HumanMessage, ToolMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode


load_dotenv()

llm = init_chat_model(model="gemini-2.5-flash", model_provider="google-genai", temperature=0)

stdio_param = StdioServerParameters(
    command="uvx",
    args=["--from", "d365fo-client", "d365fo-mcp-server"],
    env={
        "D365FO_BASE_URL": os.getenv("D365FO_BASE_URL"),
        "D365FO_CLIENT_ID": os.getenv("D365FO_CLIENT_ID"),
        "D365FO_CLIENT_SECRET": os.getenv("D365FO_CLIENT_SECRET"),
        "D365FO_TENANT_ID": os.getenv("D365FO_TENANT_ID"),
    }
)

class SalesOrderline(BaseModel):
    line_number: int| None = None
    line_amount: float| None = None
    line_quantity: int| None = None
    line_price: float| None = None
    line_total: float| None = None
    line_product: str| None = None
    line_customer: str| None = None
    line_status: str| None = None
    line_date: str| None = None


class SalesOrder(BaseModel):
    so_number: str | None = None
    so_date: str| None = None
    so_amount: float| None = None
    so_status: str| None = None
    so_customer: str| None = None
    so_customer_name: str | None=None
    so_product: str| None = None
    so_quantity: int| None = None
    so_price: float| None = None
    so_total: float| None = None
    so_lines: List[SalesOrderline]| None = None

class AgentGraph(MessagesState):
    structured_output: SalesOrder | None=None
    so_number: str | None = None

def build_graph(tools: list):

    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    def draft_node(state: AgentGraph):
        res = llm_with_tools.invoke([
            SystemMessage(content="""You are a helpful assistant that can help with sales order management.
                                   1. You need to use the tools to get the information on Sales Order.
                                   2. Don assume any of the details that are returned from the tools. Just use the tools to get the information.
                                   """),
            *state["messages"],
        ])
        return {"messages": [res]}

    def formatted_node(state:AgentGraph):
        
        all_tool_messages = []
        for msg in state["messages"]:
            if hasattr(msg, "content") and hasattr(msg, "name"):
                all_tool_messages.append(f"{msg.name}:\n{msg.content}")

        collection = "".join(all_tool_messages)
        formatted_llm = llm.with_structured_output(SalesOrder)

        formatted_res = formatted_llm.invoke([
            HumanMessage(content=f""" Extract ALL purchase order details including header AND line items
                from the data below. Make sure to populate the lines array
                with every line item found.

                Data:
                {collection}
                """)
        ])
        return {"structured_output":formatted_res}
    ACT = ""
    FORMAT = ""
    AGENT_RESPONSE = ""


    def should_continue(state:AgentGraph) -> Literal["act","format"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "act"
        return "format"

    flow = StateGraph(AgentGraph)
    flow.add_node("agent_response",draft_node)
    flow.add_node("format", formatted_node)
    flow.set_entry_point("agent_response")
    flow.add_node("act", tool_node)
    flow.add_edge("act", "agent_response")
    flow.add_edge("format",END)
    flow.add_conditional_edges("agent_response",should_continue, path_map={"act":"act", "format":"format"})
    
    return flow.compile()

async def main():
    try:
        async with stdio_client(stdio_param) as (read, write):
            async with ClientSession(read_stream=read,write_stream=write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                graph = build_graph(tools)

                result = await graph.ainvoke({
                    "messages": [HumanMessage(content="""
                        For Sales order number '000011':
                        1. Get the sales order header details
                        2. Get all the sales order LINE ITEMS
                        3. From legal entity "USMF"
                        Return everything you find.
                    """)],
                    "structured_output": None,
                    "so_number": "000011"

                })

                so: SalesOrder = result["structured_output"]

                print("===== SALES ORDER =====")
                print(f"SO Number  : {so.so_number}")
                print(f"Customer     : {so.so_customer_name} ({so.so_customer})")
                print(f"Status     : {so.so_status}")
                
                if so.so_lines:
                    for line in so.so_lines:  
                        print(f"Line Number  : {line.line_number}")
                        print(f"Line Amount  : {line.line_amount}")
                        print(f"Line Quantity: {line.line_quantity}")
                else:
                    print("\n⚠️  No line items returned.")
                    print("    Check if the MCP tool for SO lines is named differently:")
                    for t in tools:
                        if "sales" in t.name.lower() or "line" in t.name.lower():
                            print(f"    → {t.name}: {t.description}")
    finally:
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())


