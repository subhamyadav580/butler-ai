# Gmail tabs/folders mapped to the same search queries Gmail's UI uses
CATEGORIES = {
    # Inbox tabs
    "primary": "in:inbox category:primary",
    "promotions": "in:inbox category:promotions",
    "social": "in:inbox category:social",
    "updates": "in:inbox category:updates",
    "forums": "in:inbox category:forums",
    "purchases": "category:purchases",
    # Sidebar folders
    "inbox": "in:inbox",
    "starred": "is:starred",
    "snoozed": "in:snoozed",
    "sent": "in:sent",
    "drafts": "in:drafts",
    "important": "is:important",
    "spam": "in:spam",
    "trash": "in:trash",
    "all": "in:anywhere",
}

DEFAULT_CATEGORY = "primary"

# Spam/trash are hidden from the API unless explicitly included
SPAM_TRASH_CATEGORIES = ("spam", "trash", "all")

# Categories where the recipient matters more than the sender
OUTGOING_CATEGORIES = ("sent", "drafts")
