import asyncio
import os
from httpx import Response
from langchain_core.messages import HumanMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from langchain_mcp_adapters.tools import load_mcp_tools

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

async def main():
    async with stdio_client(stdio_client_params) as (read, write):
        async with ClientSession(read_stream=read, write_stream=write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            # print(f"number of D365 tools: {len(tools)}")
            # for t in tools:
            #     print(f"--{t.name}")
            agent = create_react_agent(llm, tools)
            Response = await agent.ainvoke({"messages":[HumanMessage(content="Can you give me the deatils of purchase order number= '000011' ")]})
            print(Response)



if __name__ == "__main__":
    asyncio.run(main())