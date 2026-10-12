"""Build outgoing emails (replies, new mail) as Gmail API raw messages.

Pure functions: no network. Replies thread correctly in every mail client:
same Gmail threadId, "Re: " subject, In-Reply-To and References headers.
"""

import base64
from email.message import EmailMessage
from email.utils import getaddresses


def _addresses(*header_values):
    """Unique email addresses from header values like 'A <a@x>, b@y'."""
    seen, result = set(), []
    for _, addr in getaddresses([v for v in header_values if v]):
        key = addr.lower()
        if addr and key not in seen:
            seen.add(key)
            result.append(addr)
    return result


def reply_recipients(original, my_address, reply_all=False):
    """(to, cc) for a reply. Reply-To wins over From; reply-all adds the other
    recipients; never includes the sender's own address."""
    me = (my_address or "").lower()
    to = [a for a in _addresses(original.get("reply_to") or original["from"]) if a.lower() != me]
    cc = []
    if reply_all:
        others = _addresses(original.get("to"), original.get("cc"))
        cc = [a for a in others if a.lower() != me and a.lower() not in {t.lower() for t in to}]
    if not to:   # replying to a mail I sent myself: answer its recipients
        to = [a for a in _addresses(original.get("to")) if a.lower() != me]
    return to, cc


def reply_subject(subject):
    subject = (subject or "").strip()
    return subject if subject.lower().startswith("re:") else f"Re: {subject}".strip()


def build_message(to, subject, body, cc=None, in_reply_to=None, references=None):
    message = EmailMessage()
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = " ".join(filter(None, [references, in_reply_to]))
    message.set_content(body)
    return message


def to_raw(message):
    """Gmail API wants the whole RFC 2822 message base64url-encoded."""
    return base64.urlsafe_b64encode(message.as_bytes()).decode()
