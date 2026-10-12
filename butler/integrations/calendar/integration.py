"""Google Calendar as a Butler integration: read events, create/move/delete with approval."""

import asyncio

from butler.config import GOOGLE_CLIENT_SECRET_FILE
from butler.integrations.base import Integration
from butler.integrations.google_oauth import google_status

from .client import Calendar
from .config import SCOPES, TOKEN_FILE
from .tools import CALENDAR_TOOLS

RULES = (
    "Google Calendar (the user's primary calendar):\n"
    "- All times are in the user's time zone (above). Pass start/end as "
    "'YYYY-MM-DDTHH:MM' for timed events, or 'YYYY-MM-DD' for all-day. "
    "Work out relative dates ('tomorrow', 'next Friday', 'in 2 hours') "
    "from the current time above.\n"
    "- 'What's on my calendar', 'am I free', 'when is my next…' → "
    "list_calendar_events or find_free_time. Present events as time, title "
    "and (if any) place or Meet link.\n"
    "- Creating: if no end time is given, use 1 hour (30 minutes for a "
    "'call' or 'quick' meeting). Don't ask about optional details "
    "(description, location). Ask only if the date or start time is missing.\n"
    "- Guests: adding attendees makes Google EMAIL them an invitation. Only "
    "add people the user named, with real email addresses; if you only have "
    "a name, look the address up in Gmail (get_emails with sender=<name>) or "
    "ask. Never invent an address.\n"
    "- To change or delete an event, first find it with list_calendar_events "
    "(by date or query) to get its id; if several match, ask which one.\n"
    "- Creating, changing and deleting ask the user for approval "
    "automatically, so just call the tool. Never claim it happened unless the "
    "tool's status says created, updated or deleted.\n"
)


class CalendarIntegration(Integration):
    name = "calendar"
    title = "Google Calendar"
    description = "See your schedule, find free time, and add, move or cancel events."
    login_command = "calendar-login"
    can_connect = True
    tool_labels = {
        "list_calendar_events": "Checking your calendar",
        "get_calendar_event": "Loading the event",
        "find_free_time": "Finding free time",
        "create_calendar_event": "Adding the event",
        "update_calendar_event": "Updating the event",
        "delete_calendar_event": "Deleting the event",
    }
    examples = [
        "What's on my calendar tomorrow?",
        "Block 30 min for a call on Friday at 4 pm",
    ]

    def tools(self):
        return CALENDAR_TOOLS

    def rules(self, tool_names):
        return RULES

    def status(self, loaded_tool_names):
        return google_status(TOKEN_FILE, SCOPES, str(GOOGLE_CLIENT_SECRET_FILE), "Google Calendar")

    async def connect(self):
        # Opens a browser on this machine, then one read to prove the API works
        await asyncio.to_thread(lambda: Calendar(interactive=True).profile())

    def login(self):
        from .login import main
        main()


INTEGRATION = CalendarIntegration()
