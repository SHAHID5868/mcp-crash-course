import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_stdio():
    """Test community package - d365fo-client"""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    print("\n=== Testing STDIO (d365fo-client) ===")
    try:
        params = StdioServerParameters(
            command="uvx",
            args=["--from", "d365fo-client", "d365fo-mcp-server"],
            env={
                "D365FO_BASE_URL": os.getenv("D365FO_BASE_URL"),
                "D365FO_CLIENT_ID": os.getenv("D365FO_CLIENT_ID"),
                "D365FO_CLIENT_SECRET": os.getenv("D365FO_CLIENT_SECRET"),
                "D365FO_TENANT_ID": os.getenv("D365FO_TENANT_ID"),
            }
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print(f"✅ STDIO works! Found {len(tools.tools)} tools")
                for t in tools.tools:
                    print(f"   - {t.name}")
    except Exception as e:
        print(f"❌ STDIO failed: {e}")


async def test_sse():
    """Test Microsoft's official SSE endpoint"""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    print("\n=== Testing SSE (Microsoft Official) ===")
    base_url = os.getenv("D365FO_BASE_URL")  # e.g. https://your-env.dynamics.com

    try:
        async with sse_client(
            f"{base_url}/mcp",
            headers={"Authorization": f"Bearer {os.getenv('D365FO_ACCESS_TOKEN')}"}
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print(f"✅ SSE works! Found {len(tools.tools)} tools")
                for t in tools.tools:
                    print(f"   - {t.name}")
    except Exception as e:
        print(f"❌ SSE failed: {e}")


async def main():
    await test_stdio()
    await test_sse()

if __name__ == "__main__":
    asyncio.run(main())