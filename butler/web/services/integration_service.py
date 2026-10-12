"""Status and connection of integrations (Gmail, Swiggy, ...).

Connecting runs the same OAuth login as the CLI: a browser opens on the
machine running Butler. That's the self-hosted model — the person running
the server is the person whose accounts are connected.
"""

import asyncio
import os
import time

from google.oauth2.credentials import Credentials

from butler.config import CALENDAR_TOKEN_FILE, GMAIL_TOKEN_FILE, GOOGLE_CLIENT_SECRET_FILE
from butler.integrations.calendar import Calendar
from butler.integrations.calendar.config import SCOPES as CALENDAR_SCOPES
from butler.integrations.gmail.auth import get_gmail_service
from butler.integrations.gmail.config import SCOPES as GMAIL_SCOPES
from butler.integrations.swiggy import get_swiggy_tools, smoke_test
from butler.integrations.swiggy.config import SERVERS as SWIGGY_SERVERS
from butler.integrations.swiggy.auth import FileTokenStorage


class UnknownIntegration(Exception):
    pass


class IntegrationService:
    def __init__(self, on_connected=None):
        # Called after a successful connect, e.g. to reload the agent's tools
        self._on_connected = on_connected
        self._connecting = {}  # name -> asyncio.Task
        self._errors = {}      # name -> last connect error

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def list_status(self, swiggy_services):
        """swiggy_services: the Swiggy services the running agent has loaded."""
        return [
            self._gmail_status(),
            self._calendar_status(),
            self._swiggy_status(set(swiggy_services)),
        ]

    def _common(self, name):
        return {
            "connecting": name in self._connecting,
            "error": self._errors.get(name),
        }

    def _gmail_status(self):
        status = {
            "name": "gmail",
            "title": "Gmail",
            "description": "Read and search your mailbox (read-only).",
            **self._common("gmail"),
        }

        if not GOOGLE_CLIENT_SECRET_FILE.exists():
            return {
                **status,
                "state": "needs_setup",
                "detail": (
                    "Create a Google OAuth client (Desktop app) and save it as "
                    f"{GOOGLE_CLIENT_SECRET_FILE.name} in the secrets/ folder. "
                    "See the README."
                ),
            }

        if GMAIL_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), GMAIL_SCOPES)
            if creds.valid or creds.refresh_token:
                return {**status, "state": "connected", "detail": "Connected."}

        return {**status, "state": "disconnected", "detail": "Not connected yet."}

    def _calendar_status(self):
        status = {
            "name": "calendar",
            "title": "Google Calendar",
            "description": "See your schedule, find free time, and add, move or cancel events.",
            **self._common("calendar"),
        }
        if not GOOGLE_CLIENT_SECRET_FILE.exists():
            return {
                **status,
                "state": "needs_setup",
                "detail": "Set up the Google OAuth client first (same as Gmail). See the README.",
            }
        if CALENDAR_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES)
            if creds.valid or creds.refresh_token:
                return {**status, "state": "connected", "detail": "Connected."}
        return {**status, "state": "disconnected", "detail": "Not connected yet."}

    def _swiggy_status(self, loaded):
        status = {
            "name": "swiggy",
            "title": "Swiggy",
            "description": (
                "Food delivery, Instamart groceries and Dineout table "
                "bookings (India). Enabled: " + ", ".join(SWIGGY_SERVERS) + "."
            ),
            **self._common("swiggy"),
        }

        storage = FileTokenStorage()
        expires_at = storage.get_expires_at() if os.path.exists(storage.path) else None
        has_token = bool(expires_at) and expires_at > time.time()

        if not has_token:
            detail = "Login expired." if expires_at else "Not connected yet."
            return {**status, "state": "disconnected", "detail": detail}

        days_left = (expires_at - time.time()) / 86400
        detail = f"Connected. Login expires in {days_left:.1f} days (Swiggy limit)."
        missing = set(SWIGGY_SERVERS) - loaded
        if not loaded:
            detail += " Reload the agent to start using it."
        elif missing:
            detail += (
                f" Not loaded right now: {', '.join(sorted(missing))} "
                "(Swiggy may be rate-limiting). Reload the agent to retry."
            )
        return {**status, "state": "connected", "detail": detail, "expires_at": expires_at}

    # ------------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------------

    def connect(self, name):
        """Start the login flow in the background; returns immediately."""
        flows = {
            "gmail": self._connect_gmail,
            "calendar": self._connect_calendar,
            "swiggy": self._connect_swiggy,
        }
        if name not in flows:
            raise UnknownIntegration(name)

        if name in self._connecting:
            return  # already in progress

        self._errors.pop(name, None)
        task = asyncio.create_task(self._run(name, flows[name]))
        self._connecting[name] = task

    async def _run(self, name, flow):
        try:
            await flow()
            if self._on_connected:
                await self._on_connected(name)
        except BaseException as error:  # noqa: BLE001 — surfaced to the UI
            self._errors[name] = _describe(error)
        finally:
            self._connecting.pop(name, None)

    async def _connect_gmail(self):
        if not GOOGLE_CLIENT_SECRET_FILE.exists():
            raise RuntimeError("Google OAuth client file is missing; see README.")
        # Opens a browser on this machine and saves the token
        service = await asyncio.to_thread(get_gmail_service, interactive=True)
        await asyncio.to_thread(
            lambda: service.users().getProfile(userId="me").execute()
        )

    async def _connect_calendar(self):
        if not GOOGLE_CLIENT_SECRET_FILE.exists():
            raise RuntimeError("Google OAuth client file is missing; see README.")
        # Opens a browser on this machine; then one read to prove the API works
        await asyncio.to_thread(lambda: Calendar(interactive=True).profile())

    async def _connect_swiggy(self):
        # Opens a browser on this machine for phone + OTP, saves the token
        tools = await get_swiggy_tools(interactive=True)
        await smoke_test(tools)


def _describe(error):
    # MCP errors arrive wrapped in ExceptionGroups; show the innermost cause
    while getattr(error, "exceptions", None):
        error = error.exceptions[0]
    return f"{type(error).__name__}: {error}"
