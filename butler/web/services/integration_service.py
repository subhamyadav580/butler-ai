"""Status and connection of integrations, for the web UI's Integrations page.

Generic: every integration describes its own status and connect flow
(butler/integrations/<name>/integration.py); this service only loops over
the registry and runs logins in the background.

Connecting runs the same login as the CLI: a browser opens on the machine
running Butler. That's the self-hosted model: the person running the server
is the person whose accounts are connected.
"""

import asyncio

from butler.integrations.registry import INTEGRATIONS, get_integration


class UnknownIntegration(Exception):
    pass


class IntegrationService:
    def __init__(self, on_connected=None):
        # Called after a successful connect, with the integration
        self._on_connected = on_connected
        self._connecting = {}  # name -> asyncio.Task
        self._errors = {}      # name -> last connect error

    def list_status(self, loaded_tool_names):
        """loaded_tool_names: tools the running agent has (some integrations
        report e.g. "connected, but reload the agent")."""
        statuses = []
        for integration in INTEGRATIONS:
            try:
                status = integration.status(set(loaded_tool_names))
            except Exception as error:  # noqa: BLE001 — one broken card mustn't break the page
                status = {"state": "needs_setup", "detail": f"Status check failed: {_describe(error)}"}
            statuses.append({
                "name": integration.name,
                "title": integration.title,
                "description": integration.description,
                "can_connect": integration.can_connect,
                "options": integration.options(),
                "connecting": integration.name in self._connecting,
                "error": self._errors.get(integration.name),
                **status,
            })
        return statuses

    def set_option(self, name, key, value):
        integration = get_integration(name)
        if integration is None:
            raise UnknownIntegration(name)
        integration.set_option(key, value)     # KeyError for unknown options

    def connect(self, name):
        """Start the integration's login in the background; returns immediately."""
        integration = get_integration(name)
        if integration is None or not integration.can_connect:
            raise UnknownIntegration(name)
        if name in self._connecting:
            return  # already in progress

        self._errors.pop(name, None)
        self._connecting[name] = asyncio.create_task(self._run(integration))

    async def _run(self, integration):
        try:
            await integration.connect()
            if self._on_connected:
                await self._on_connected(integration)
        except BaseException as error:  # noqa: BLE001 — surfaced to the UI
            self._errors[integration.name] = _describe(error)
        finally:
            self._connecting.pop(integration.name, None)


def _describe(error):
    # MCP errors arrive wrapped in ExceptionGroups; show the innermost cause
    while getattr(error, "exceptions", None):
        error = error.exceptions[0]
    return f"{type(error).__name__}: {error}"
