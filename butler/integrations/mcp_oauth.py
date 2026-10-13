"""OAuth login for remote MCP servers (Swiggy, Zepto, …), shared by every
integration that talks to one.

The MCP library does the protocol: it discovers the auth server, registers a
client (dynamic client registration), runs PKCE and refreshes tokens when the
server allows it. This module supplies the parts that are ours:

- FileTokenStorage: the token + registered client in secrets/<name>_token.json
- LocalCallback: a one-shot localhost server that catches the login redirect
- make_auth(): the httpx auth for MCP requests; opens a browser only when
  interactive, otherwise raises LoginRequired so the agent can say "log in"
"""

import asyncio
import json
import os
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

CLIENT_NAME = "Butler"


class LoginRequired(Exception):
    """A login is needed but we can't open a browser (bot/agent context)."""


def is_login_error(error):
    """True if this error (or one nested in an ExceptionGroup) means 'log in'."""
    if isinstance(error, LoginRequired):
        return True
    return any(is_login_error(e) for e in getattr(error, "exceptions", []))


def describe_error(error):
    """Innermost cause of a (possibly nested) MCP error, as one short line."""
    while getattr(error, "exceptions", None):
        error = error.exceptions[0]
    return f"{type(error).__name__}: {error}"[:200]


class FileTokenStorage(TokenStorage):
    """Persist the OAuth token and registered client in a JSON file."""

    def __init__(self, path):
        self.path = str(path)

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

    def has_tokens(self):
        return bool(self._load().get("tokens"))

    def client_id(self):
        return self._load().get("client", {}).get("client_id")

    def has_refresh_token(self):
        return bool(self._load().get("tokens", {}).get("refresh_token"))

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

    def take_tokens(self):
        """Remove the saved login (keeping the registered client) so the next
        connection must log in again. Returns what was removed, for put_back()."""
        data = self._load()
        removed = {k: data.pop(k) for k in ("tokens", "expires_at") if k in data}
        self._save(data)
        return removed

    def put_back(self, removed):
        data = self._load()
        if "tokens" not in data:               # only if the new login didn't save one
            data.update(removed)
            self._save(data)

    async def get_client_info(self):
        client = self._load().get("client")
        return OAuthClientInformationFull.model_validate(client) if client else None

    async def set_client_info(self, client_info):
        data = self._load()
        data["client"] = client_info.model_dump(mode="json", exclude_none=True)
        self._save(data)


class LocalCallback:
    """Tiny localhost server that catches the OAuth redirect (?code=&state=)."""

    def __init__(self, port, service):
        self.port = port
        self.service = service             # "Swiggy", shown on the result page
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
            body = f"{self.service} login complete. You can close this tab."
            if not self._result.done():
                self._result.set_result(
                    (params["code"][0], params.get("state", [None])[0])
                )
        else:
            error = params.get("error", ["no code in callback"])[0]
            body = f"{self.service} login failed: {error}"
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


def make_auth(*, service, server_url, token_file, redirect_port, login_command,
              interactive=False, scope=None, refresh=True):
    """Build the httpx auth used for every request to one MCP service.

    service        "Swiggy": used in messages
    server_url     the MCP server whose auth server we log in to
    redirect_port  localhost port for the login redirect (http://localhost:<port>/callback)
    scope          None lets the MCP library pick the scopes the server advertises
    refresh        False if the server issues refresh tokens but rejects them
    interactive    True opens a browser for login when needed; False raises
                   LoginRequired instead (the agent and bots)
    """
    callback = LocalCallback(redirect_port, service)

    async def redirect_handler(authorization_url):
        if not interactive:
            raise LoginRequired(f"{service} login required. Run: {login_command}")
        await callback.start()
        print(f"Opening browser for {service} login...\n", authorization_url)
        webbrowser.open(authorization_url)

    async def callback_handler():
        return await callback.wait()

    return OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name=CLIENT_NAME,
            redirect_uris=[f"http://localhost:{redirect_port}/callback"],
            grant_types=["authorization_code", "refresh_token"] if refresh else ["authorization_code"],
            response_types=["code"],
            token_endpoint_auth_method="none",
            scope=scope,
        ),
        storage=FileTokenStorage(token_file),
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
