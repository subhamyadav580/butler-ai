from langchain_mcp_adapters.client import MultiServerMCPClient

from .auth import make_auth
from .config import SERVERS


def get_client(interactive=False):
    return MultiServerMCPClient({
        f"swiggy_{name}": {
            "transport": "streamable_http",
            "url": url,
            "auth": make_auth(interactive),
        }
        for name, url in SERVERS.items()
    })


async def get_swiggy_tools(interactive=False):
    """Load every tool from the enabled Swiggy MCP servers as LangChain tools."""
    return await get_client(interactive).get_tools()
