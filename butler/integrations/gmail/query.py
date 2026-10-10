from .categories import CATEGORIES, DEFAULT_CATEGORY


def build_query(
    category=None,
    sender=None,
    to=None,
    subject=None,
    text=None,
    unread=None,
    has_attachment=False,
    after=None,
    before=None,
):
    """Combine a category with optional filters into one Gmail search query.

    Defaults to Primary. Dates use Gmail's YYYY/MM/DD format,
    e.g. after="2026/10/01".
    """
    category = category or DEFAULT_CATEGORY

    if category not in CATEGORIES:
        raise ValueError(
            f"Unknown category '{category}'. "
            f"Choose from: {', '.join(CATEGORIES)}"
        )

    parts = [CATEGORIES[category]]

    if sender:
        parts.append(f"from:({sender})")
    if to:
        parts.append(f"to:({to})")
    if subject:
        parts.append(f'subject:("{subject}")')
    if text:
        parts.append(text)
    if unread is True:
        parts.append("is:unread")
    elif unread is False:
        parts.append("is:read")
    if has_attachment:
        parts.append("has:attachment")
    if after:
        parts.append(f"after:{after}")
    if before:
        parts.append(f"before:{before}")

    return " ".join(parts)
