"""The system prompt: a short base, plus one section per loaded integration.

Each integration writes its own section (its `rules()`, next to its tools in
butler/integrations/<name>/integration.py); this module only assembles them.
"""

from datetime import datetime

from butler.config import local_tz


def system_prompt(sections=()):
    """sections: the rules of each integration this user can use right now."""
    now = datetime.now(local_tz())
    prompt = (
        "You are a helpful personal assistant. Answer general questions "
        "directly from your own knowledge. Use tools only when a request "
        "needs the user's own data or current information; a single message "
        "may need several tools.\n"
        f"Now: {now:%A %d %B %Y, %H:%M} ({now.tzname()}, UTC{now:%z}). "
        f"Today as YYYY/MM/DD: {now:%Y/%m/%d}.\n"
    )
    return prompt + "".join("\n" + s for s in sections if s)
