import asyncio
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent

load_dotenv()

# llm = init_chat_model(model="gemini-2.5-flash", model_provider="google-genai", temperature=0)
llm = init_chat_model(model="llama-3.3-70b-versatile", model_provider="groq", temperature=0)
stdio_server_params = StdioServerParameters(
    command="python",
    args=["/Users/shahid/PyCharmMiscProject/mcp-crash-course/servers/math_server.py"]
)

async def main():
    async with stdio_client(stdio_server_params) as (read,write):
        async with ClientSession(read_stream= read, write_stream=write) as session:
            await session.initialize()
            print("session initialized")
            tools = await load_mcp_tools(session)
            print(tools)
            agent = create_agent(llm,tools)

            result = await agent.ainvoke({"messages": [HumanMessage(content="What is 2+2")]})
            print(result["messages"][-1].content)



if __name__ == "__main__":
    asyncio.run(main())
