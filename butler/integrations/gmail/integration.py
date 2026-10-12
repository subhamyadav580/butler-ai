"""Gmail as a Butler integration: read-only mail tools."""

import asyncio

from butler.config import GOOGLE_CLIENT_SECRET_FILE
from butler.integrations.base import Integration
from butler.integrations.google_oauth import google_status

from .auth import get_gmail_service
from .config import SCOPES, SEND_SCOPES, TOKEN_FILE
from .settings import send_enabled, set_send_enabled
from .tools import GMAIL_TOOLS, GMAIL_WRITE_TOOLS

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


WRITE_RULES = (
    "- Replying and sending are ON. When the user asks to reply or send: "
    "write the message yourself (concise, in the user's voice, no "
    "placeholders like [Your Name]) and call reply_to_email or send_email. "
    "The user sees the exact text and approves or rejects it, so don't ask "
    "'shall I send this?' first. If they say 'draft' or want to check it "
    "first, use create_draft (saved in Gmail Drafts, never sent).\n"
    "- To reply, first FIND the email with get_emails (sender, subject or "
    "text, category 'all' if unsure) and use its id. Only use pick_email "
    "when several emails match and you can't tell which one is meant.\n"
    "- Replies go to the original sender (reply_all only when asked). For a "
    "new email, only use addresses the user gave or that you found in their "
    "mail; never invent one. Never claim a mail was sent unless the tool's "
    "status is 'sent'.\n"
)

WRITE_OFF_RULES = (
    "- Replying and sending are OFF. If the user asks to reply, send or "
    "draft, say it's switched off and that they can turn on 'Allow replying "
    "& sending' on the Gmail card in the web UI's Integrations page.\n"
)


class GmailIntegration(Integration):
    name = "gmail"
    title = "Gmail"
    description = "Read and search your mailbox. Optionally reply and send, always with your approval."
    login_command = "gmail-login"
    can_connect = True
    tool_labels = {
        "get_emails": "Searching your mail",
        "pick_email": "Fetching emails",
        "read_email": "Reading the email",
        "count_unread": "Counting unread mail",
        "inbox_overview": "Checking your inbox",
        "reply_to_email": "Writing your reply",
        "send_email": "Writing your email",
        "create_draft": "Saving the draft",
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
        # Write tools are always loaded but check the switch when called, so
        # turning it on/off applies at once in every process (web, Telegram)
        return GMAIL_TOOLS + GMAIL_WRITE_TOOLS

    def rules(self, tool_names):
        return RULES + (WRITE_RULES if send_enabled() else WRITE_OFF_RULES)

    def status(self, loaded_tool_names):
        return google_status(
            TOKEN_FILE, SCOPES, str(GOOGLE_CLIENT_SECRET_FILE), "Gmail",
            wanted_scopes=SEND_SCOPES if send_enabled() else None,
            wanted_reason="Replying & sending is on, but Gmail hasn't granted permission to send yet.",
        )

    def options(self):
        return [{
            "key": "send_enabled",
            "label": "Allow replying & sending",
            "description": "Butler can reply, send and save drafts. Every reply or new email waits for your Approve.",
            "value": send_enabled(),
        }]

    def set_option(self, key, value):
        if key != "send_enabled":
            raise KeyError(key)
        set_send_enabled(value)

    async def connect(self):
        # Always opens a fresh Google login in a browser on this machine (asking
        # for sending access too when that's switched on), then proves it works
        service = await asyncio.to_thread(get_gmail_service, interactive=True, force_login=True)
        await asyncio.to_thread(lambda: service.users().getProfile(userId="me").execute())

    def login(self):
        from .login import main
        main()


INTEGRATION = GmailIntegration()
