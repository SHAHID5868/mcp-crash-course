from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import asyncio
load_dotenv()

llm = init_chat_model(model="gemini-2.5-flash", model_provider="google-genai", temperature=0)

async def main():
    print("Hello MCP")

if __name__ == "__main__":
    asyncio.run(main())