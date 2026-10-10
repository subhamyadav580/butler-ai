import asyncio
import json
import os
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from .config import (
    CLIENT_NAME,
    LOGIN_COMMAND,
    REDIRECT_PORT,
    REDIRECT_URI,
    SCOPES,
    AUTH_SERVER_URL,
    TOKEN_FILE,
)


class SwiggyLoginRequired(Exception):
    """Raised when a Swiggy login is needed but we can't open a browser."""


def is_login_error(error):
    """True if this error (or one nested in an ExceptionGroup) means 'log in'."""
    if isinstance(error, SwiggyLoginRequired):
        return True
    return any(is_login_error(e) for e in getattr(error, "exceptions", []))


def describe_error(error):
    """Innermost cause of a (possibly nested) MCP error, as one short line."""
    while getattr(error, "exceptions", None):
        error = error.exceptions[0]
    return f"{type(error).__name__}: {error}"[:200]


class FileTokenStorage(TokenStorage):
    """Persist the OAuth token and registered client in a JSON file."""

    def __init__(self, path=TOKEN_FILE):
        self.path = path

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path) as f:
            return json.load(f)

    def _save(self, data):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(self.path, 0o600)

    async def get_tokens(self):
        tokens = self._load().get("tokens")
        return OAuthToken.model_validate(tokens) if tokens else None

    async def set_tokens(self, tokens):
        data = self._load()
        data["tokens"] = tokens.model_dump(mode="json", exclude_none=True)
        if tokens.expires_in:
            data["expires_at"] = time.time() + tokens.expires_in
        self._save(data)

    def get_expires_at(self):
        """When the access token expires (epoch seconds), if known."""
        data = self._load()
        if "expires_at" in data:
            return data["expires_at"]
        # Older token files: estimate from when the file was last written
        expires_in = data.get("tokens", {}).get("expires_in")
        if expires_in:
            return os.path.getmtime(self.path) + expires_in
        return None

    async def get_client_info(self):
        client = self._load().get("client")
        return OAuthClientInformationFull.model_validate(client) if client else None

    async def set_client_info(self, client_info):
        data = self._load()
        data["client"] = client_info.model_dump(mode="json", exclude_none=True)
        self._save(data)


class LocalCallback:
    """Tiny localhost server that catches the OAuth redirect (?code=&state=)."""

    def __init__(self, port=REDIRECT_PORT):
        self.port = port
        self._result = None
        self._server = None

    async def start(self):
        self._result = asyncio.get_running_loop().create_future()
        self._server = await asyncio.start_server(self._handle, "localhost", self.port)

    async def _handle(self, reader, writer):
        request_line = (await reader.readline()).decode()
        # Drain headers
        while (await reader.readline()) not in (b"\r\n", b"\n", b""):
            pass

        path = request_line.split(" ")[1] if " " in request_line else "/"
        params = parse_qs(urlparse(path).query)

        if "code" in params:
            body = "Swiggy login complete. You can close this tab."
            if not self._result.done():
                self._result.set_result(
                    (params["code"][0], params.get("state", [None])[0])
                )
        else:
            error = params.get("error", ["no code in callback"])[0]
            body = f"Swiggy login failed: {error}"
            if not self._result.done():
                self._result.set_exception(RuntimeError(body))

        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\n"
            b"Connection: close\r\n\r\n" + body.encode()
        )
        await writer.drain()
        writer.close()

    async def wait(self):
        try:
            return await self._result
        finally:
            self._server.close()
            await self._server.wait_closed()


def make_auth(interactive=False):
    """Build the httpx auth used for every Swiggy MCP request.

    interactive=True opens a browser for phone + OTP login when needed.
    interactive=False (bot/agent) raises SwiggyLoginRequired instead.
    """
    callback = LocalCallback()

    async def redirect_handler(authorization_url):
        if not interactive:
            raise SwiggyLoginRequired(
                f"Swiggy login required. Run: {LOGIN_COMMAND}"
            )
        await callback.start()
        print("Opening browser for Swiggy login...\n", authorization_url)
        webbrowser.open(authorization_url)

    async def callback_handler():
        return await callback.wait()


    return OAuthClientProvider(
        server_url=AUTH_SERVER_URL,
        client_metadata=OAuthClientMetadata(
            client_name=CLIENT_NAME,
            redirect_uris=[REDIRECT_URI],
            # Swiggy v1 issues a refresh_token but rejects refresh (401)
            grant_types=["authorization_code"],
            response_types=["code"],
            token_endpoint_auth_method="none",
            scope=SCOPES,
        ),
        storage=FileTokenStorage(),
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
