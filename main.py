import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent

load_dotenv()

llm = init_chat_model(model="gemini-2.5-flash", model_provider="google-genai", temperature=0)

stdio_server_params = StdioServerParameters(
    command="python",
    args=["/Users/shahid/PyCharmMiscProject/mcp-crash-course/servers/math_server.py"]
)

async def main():
    print("Hello from mcp-crash-course!")


if __name__ == "__main__":
    asyncio.run(main())
