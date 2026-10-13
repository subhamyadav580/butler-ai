"""Swiggy login: the shared MCP OAuth flow (../mcp_oauth.py) with Swiggy's settings."""

from butler.integrations import mcp_oauth
from butler.integrations.mcp_oauth import LoginRequired, describe_error, is_login_error

from .config import AUTH_SERVER_URL, LOGIN_COMMAND, REDIRECT_PORT, SCOPES, TOKEN_FILE

SwiggyLoginRequired = LoginRequired

__all__ = ["FileTokenStorage", "SwiggyLoginRequired", "describe_error", "is_login_error", "make_auth"]


class FileTokenStorage(mcp_oauth.FileTokenStorage):
    def __init__(self, path=TOKEN_FILE):
        super().__init__(path)


def make_auth(interactive=False):
    return mcp_oauth.make_auth(
        service="Swiggy",
        server_url=AUTH_SERVER_URL,
        token_file=TOKEN_FILE,
        redirect_port=REDIRECT_PORT,
        login_command=LOGIN_COMMAND,
        interactive=interactive,
        scope=SCOPES,
        refresh=False,       # Swiggy v1 issues a refresh_token but rejects refresh (401)
    )
