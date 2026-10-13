from langchain_mcp_adapters.client import MultiServerMCPClient

from .auth import make_auth
from .config import SERVER_NAME, SERVER_URL


async def get_zepto_tools(interactive=False):
    """Zepto's MCP tools as LangChain tools (names prefixed with "zepto_")."""
    client = MultiServerMCPClient(
        {SERVER_NAME: {"transport": "streamable_http", "url": SERVER_URL, "auth": make_auth(interactive)}},
        tool_name_prefix=True,
    )
    return await client.get_tools()
