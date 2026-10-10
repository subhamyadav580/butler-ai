from typing import Literal, Optional

from langchain_core.tools import tool
from langgraph.types import interrupt

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


GMAIL_TOOLS = [get_emails, pick_email, read_email, count_unread, inbox_overview]
