from typing import Literal, Optional

from langchain_core.tools import tool
from langgraph.types import interrupt

from .compose import build_message, reply_recipients, reply_subject, to_raw
from .settings import send_enabled

from .categories import CATEGORIES
from .client import Gmail


Category = Literal[tuple(CATEGORIES)]

# Bodies can be huge (newsletters); keep tool output LLM-sized
MAX_BODY_CHARS = 4000

_gmail = None


def _client():
    # Share one authenticated client across all tool calls
    global _gmail
    if _gmail is None:
        _gmail = Gmail()
    return _gmail


def _compact(email):
    return {
        "id": email["id"],
        "from": email["from"],
        "to": email["to"],
        "subject": email["subject"],
        "date": email["date"],
        "snippet": email["snippet"],
        "unread": email["unread"],
    }


@tool
def get_emails(
    category: Category = "primary",
    limit: int = 10,
    sender: Optional[str] = None,
    to: Optional[str] = None,
    subject: Optional[str] = None,
    text: Optional[str] = None,
    unread: Optional[bool] = None,
    has_attachment: bool = False,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> list[dict]:
    """List emails from a Gmail tab or folder, optionally filtered.

    Args:
        category: Gmail tab/folder. Inbox tabs: primary, promotions, social,
            updates, forums, purchases. Folders: inbox, starred, snoozed,
            sent, drafts, important, spam, trash. Use "all" to search
            everywhere. Defaults to primary.
        limit: Maximum number of emails to return (1-50).
        sender: Filter by sender name or email address.
        to: Filter by recipient name or email address.
        subject: Filter by words in the subject.
        text: Free-text search across the whole email.
        unread: True for unread only, False for read only, omit for both.
        has_attachment: Only emails with attachments.
        after: Only emails after this date, format YYYY/MM/DD.
        before: Only emails before this date, format YYYY/MM/DD.
    """
    emails = _client().get_emails(
        category,
        max(1, min(limit, 50)),
        sender=sender,
        to=to,
        subject=subject,
        text=text,
        unread=unread,
        has_attachment=has_attachment,
        after=after,
        before=before,
    )
    return [_compact(email) for email in emails]


@tool
def read_email(email_id: str) -> dict:
    """Read the full body of one email. Use an id returned by get_emails."""
    return _read(email_id)


@tool
def pick_email(
    category: Category = "primary",
    limit: int = 10,
    sender: Optional[str] = None,
    to: Optional[str] = None,
    subject: Optional[str] = None,
    text: Optional[str] = None,
    unread: Optional[bool] = None,
    has_attachment: bool = False,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> dict:
    """List emails and let the USER choose one, then return its full details.

    Use when the user wants to open, read or see the details of an email
    but has not said exactly which one. Takes the same filters as get_emails.
    """
    emails = get_emails.func(
        category, limit, sender, to, subject, text,
        unread, has_attachment, after, before,
    )

    if not emails:
        return {"status": "no_emails", "message": "No emails matched."}

    # Pause the graph; the caller resumes with {"email_id": <id or None>}.
    # (A bare None resume value is not supported by LangGraph.)
    answer = interrupt({
        "type": "pick_email",
        "question": "Which email do you want to open?",
        "emails": emails,
    })
    chosen_id = (answer or {}).get("email_id")

    if not chosen_id:
        return {
            "status": "cancelled",
            "message": (
                "The user closed the email picker on purpose. This is not an "
                "error: do not retry or apologise, just ask what they want next."
            ),
        }

    return {
        "status": "selected",
        "message": "The user picked this email. Present its details.",
        "email": _read(chosen_id),
    }


def _read(email_id):
    email = _client().get_email(email_id)
    result = _compact(email)
    result["body"] = email["body"][:MAX_BODY_CHARS]
    return result


@tool
def count_unread(category: Category = "primary") -> int:
    """Exact number of unread emails in a Gmail tab or folder."""
    return _client().unread_count(category)


@tool
def inbox_overview(limit: int = 3) -> dict:
    """Latest emails from Primary, Promotions, Social, Updates and Sent at once.

    Use when the user asks for a general summary of their mailbox.
    """
    overview = _client().get_all_categories(max(1, min(limit, 10)))
    return {
        category: [_compact(email) for email in emails]
        for category, emails in overview.items()
    }


# ----------------------------------------------------------------------
# Writing: only when "Allow replying & sending" is on (Integrations page).
# Sending always waits for the user's Approve; drafts are never sent.
# ----------------------------------------------------------------------

SENDING_OFF = (
    "Replying and sending are turned off. Tell the user to switch on "
    "'Allow replying & sending' on the Gmail card (web UI → Integrations), "
    "then click Reconnect to grant permission."
)


def _clean_list(addresses):
    return [a.strip() for a in (addresses or []) if a and a.strip()]


def _preview(to, cc, subject, body):
    lines = [f"To: {', '.join(to)}"]
    if cc:
        lines.append(f"Cc: {', '.join(cc)}")
    lines += [f"Subject: {subject}", "", body]
    return "\n".join(lines)


def _approve(question, tool_name, preview):
    # Pause until the user approves. On resume this tool runs again from the
    # top, so everything before this call must be read-only.
    answer = interrupt({
        "type": "confirm_action",
        "question": question,
        "tool": tool_name,
        "args": {},
        "details": preview,
        "restricted": True,       # sends as the owner: only the owner approves
    })
    return bool((answer or {}).get("approved"))


@tool
def reply_to_email(email_id: str, body: str, reply_all: bool = False) -> dict:
    """Reply to an email, in the same thread. The user approves the exact text first.

    Args:
        email_id: The email to reply to (from get_emails / pick_email).
        body: The reply text, written in the user's voice. Plain text.
        reply_all: Also reply to everyone else on the email (To and Cc).
    """
    if not send_enabled():
        return {"error": SENDING_OFF}
    gmail = _client()
    original = gmail.reply_context(email_id)
    to, cc = reply_recipients(original, gmail.my_address(), reply_all)
    if not to:
        return {"error": "Couldn't work out who to reply to."}
    subject = reply_subject(original["subject"])

    if not _approve("Send this reply?", "reply_to_email", _preview(to, cc, subject, body)):
        return {"status": "rejected", "message": "The user didn't approve. Nothing was sent."}

    message = build_message(to, subject, body, cc, original["message_id"], original["references"])
    sent = gmail.send_raw(to_raw(message), original["thread_id"])
    return {"status": "sent", "id": sent["id"], "to": to, "cc": cc, "subject": subject}


@tool
def send_email(to: list[str], subject: str, body: str, cc: Optional[list[str]] = None) -> dict:
    """Send a new email. The user approves the exact message first.

    Args:
        to: Recipient email addresses. Only addresses the user gave or that
            you found in their mail; never invent one.
        subject: Subject line.
        body: Plain-text body, in the user's voice.
        cc: Optional Cc addresses.
    """
    if not send_enabled():
        return {"error": SENDING_OFF}
    to, cc = _clean_list(to), _clean_list(cc)
    if not to:
        return {"error": "No recipient given."}

    if not _approve("Send this email?", "send_email", _preview(to, cc, subject, body)):
        return {"status": "rejected", "message": "The user didn't approve. Nothing was sent."}

    sent = _client().send_raw(to_raw(build_message(to, subject, body, cc)))
    return {"status": "sent", "id": sent["id"], "to": to, "cc": cc, "subject": subject}


@tool
def create_draft(
    body: str,
    reply_to_email_id: Optional[str] = None,
    to: Optional[list[str]] = None,
    subject: Optional[str] = None,
    cc: Optional[list[str]] = None,
) -> dict:
    """Save an email as a DRAFT in Gmail without sending it. The user can review
    and send it from Gmail. Use when the user says "draft" or wants to check
    the text first.

    Args:
        body: Plain-text body.
        reply_to_email_id: Make it a draft reply to this email (same thread).
        to, subject, cc: For a new email (ignored when replying).
    """
    if not send_enabled():
        return {"error": SENDING_OFF}
    gmail = _client()
    thread_id, in_reply_to, references = None, None, None
    if reply_to_email_id:
        original = gmail.reply_context(reply_to_email_id)
        to, cc = reply_recipients(original, gmail.my_address())
        subject = reply_subject(original["subject"])
        thread_id, in_reply_to, references = original["thread_id"], original["message_id"], original["references"]
    to, cc = _clean_list(to), _clean_list(cc)
    if not to:
        return {"error": "No recipient given."}

    message = build_message(to, subject or "(no subject)", body, cc, in_reply_to, references)
    draft = gmail.create_draft(to_raw(message), thread_id)
    return {"status": "draft_saved", "draft_id": draft["id"], "to": to, "subject": subject,
            "message": "Saved in Gmail Drafts. Not sent."}


GMAIL_TOOLS = [get_emails, pick_email, read_email, count_unread, inbox_overview]
GMAIL_WRITE_TOOLS = [reply_to_email, send_email, create_draft]
