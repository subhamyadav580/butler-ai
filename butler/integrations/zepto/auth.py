"""Zepto login: the shared MCP OAuth flow (../mcp_oauth.py) with Zepto's settings.

Phone + OTP in the browser. Zepto issues refresh tokens, so the login keeps
working after the access token expires.
"""

from butler.integrations import mcp_oauth

from .config import LOGIN_COMMAND, REDIRECT_PORT, SERVER_URL, TOKEN_FILE


def storage():
    return mcp_oauth.FileTokenStorage(TOKEN_FILE)


def make_auth(interactive=False):
    return mcp_oauth.make_auth(
        service="Zepto",
        server_url=SERVER_URL,
        token_file=TOKEN_FILE,
        redirect_port=REDIRECT_PORT,
        login_command=LOGIN_COMMAND,
        interactive=interactive,
    )
