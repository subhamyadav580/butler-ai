"""Gmail as a Butler integration: read-only mail tools."""

import asyncio

from butler.config import GOOGLE_CLIENT_SECRET_FILE
from butler.integrations.base import Integration
from butler.integrations.google_oauth import google_status

from .auth import get_gmail_service
from .config import SCOPES, TOKEN_FILE
from .tools import GMAIL_TOOLS

RULES = (
    "Gmail (read-only access to the user's mailbox):\n"
    "- Default to the primary category unless the user names another "
    "tab or folder. Dates for filters use YYYY/MM/DD.\n"
    "- Summarise results clearly: sender, subject and a one-line gist.\n"
    "- IMPORTANT: when the user wants to open, read, view, pick or see "
    "the details of an email and has not identified one exact email, "
    "call pick_email (with the right category and filters) instead of "
    "get_emails. Never ask the user to choose an email in plain text; "
    "pick_email shows them the list and returns the one they chose.\n"
    "- When pick_email returns status 'selected', present that email: "
    "from, date, subject and a short summary of its body.\n"
)


class GmailIntegration(Integration):
    name = "gmail"
    title = "Gmail"
    description = "Read and search your mailbox (read-only)."
    login_command = "gmail-login"
    can_connect = True
    tool_labels = {
        "get_emails": "Searching your mail",
        "pick_email": "Fetching emails",
        "read_email": "Reading the email",
        "count_unread": "Counting unread mail",
        "inbox_overview": "Checking your inbox",
    }
    examples = [
        "How many unread mails do I have in Promotions?",
        "Open a mail from LinkedIn",
    ]

    @property
    def cli_commands(self):
        from .__main__ import main as reader
        return {"gmail": reader}      # quick reader: `python -m butler gmail updates --unread`

    def tools(self):
        return GMAIL_TOOLS

    def rules(self, tool_names):
        return RULES

    def status(self, loaded_tool_names):
        return google_status(TOKEN_FILE, SCOPES, str(GOOGLE_CLIENT_SECRET_FILE), "Gmail")

    async def connect(self):
        # Opens a browser on this machine, then one call to prove it works
        service = await asyncio.to_thread(get_gmail_service, interactive=True)
        await asyncio.to_thread(lambda: service.users().getProfile(userId="me").execute())

    def login(self):
        from .login import main
        main()


INTEGRATION = GmailIntegration()
