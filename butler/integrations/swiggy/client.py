import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

from .auth import describe_error, is_login_error, make_auth
from .config import EXCLUDED_TOOLS, SERVERS

# Swiggy rate-limits bursts (HTTP 429); a short wait usually clears it
RETRY_DELAYS = (2, 5)


def _client(name, url, interactive):
    return MultiServerMCPClient(
        {name: {"transport": "streamable_http", "url": url, "auth": make_auth(interactive)}},
        # food_get_addresses vs instamart_get_addresses: names must be unique
        tool_name_prefix=True,
    )


async def _load_server(name, url, interactive):
    for attempt, delay in enumerate((0, *RETRY_DELAYS)):
        if delay:
            await asyncio.sleep(delay)
        try:
            return await _client(name, url, interactive).get_tools()
        except Exception as error:
            rate_limited = "429" in describe_error(error)
            if is_login_error(error) or not rate_limited or attempt == len(RETRY_DELAYS):
                raise


async def get_swiggy_tools(interactive=False, failures=None):
    """Load the tools of every enabled Swiggy server as LangChain tools.

    Servers load independently: if `failures` (a dict) is given, a server
    that fails for a reason other than login is recorded there and skipped,
    so one rate-limited server doesn't take the others down. Login problems
    always raise: they affect every server.
    """
    tools = []
    for name, url in SERVERS.items():
        try:
            server_tools = await _load_server(name, url, interactive)
        except Exception as error:
            if failures is None or is_login_error(error):
                raise
            failures[name] = describe_error(error)
            continue
        tools += [tool for tool in server_tools if tool.name not in EXCLUDED_TOOLS]
    return tools
