import threading

from .auth import get_gmail_service
from .categories import DEFAULT_CATEGORY, SPAM_TRASH_CATEGORIES
from .config import CREDENTIALS_FILE, TOKEN_FILE
from .parser import parse_summary, extract_body
from .query import build_query


class Gmail:
    """Read-only Gmail client with category tabs and search filters.

    Usage:
        gmail = Gmail()
        gmail.primary()
        gmail.updates(limit=10, sender="linkedin")
        gmail.sent(to="someone@example.com")
        gmail.search("haiku", unread=True)
        gmail.get_email(email_id)
    """

    def __init__(
        self,
        credentials_file=CREDENTIALS_FILE,
        token_file=TOKEN_FILE,
        interactive=False,
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        # True: may open a browser to log in when not connected yet
        self.interactive = interactive
        self._local = threading.local()

    @property
    def service(self):
        # One service per thread: the underlying httplib2 connection is not
        # thread-safe, and LangGraph runs parallel tool calls in threads
        if getattr(self._local, "service", None) is None:
            self._local.service = get_gmail_service(
                self.credentials_file,
                self.token_file,
                interactive=self.interactive,
            )
        return self._local.service

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def get_emails(self, category=None, limit=10, **filters):
        """Fetch emails from a Gmail tab/folder, optionally filtered.

        Defaults to Primary when no category is given.
        """
        category = category or DEFAULT_CATEGORY

        list_kwargs = {
            "userId": "me",
            "maxResults": limit,
            "q": build_query(category, **filters),
        }

        if category in SPAM_TRASH_CATEGORIES:
            list_kwargs["includeSpamTrash"] = True

        results = self.service.users().messages().list(**list_kwargs).execute()

        return [
            self._fetch_summary(message["id"])
            for message in results.get("messages", [])
        ]

    def get_email(self, email_id):
        """Fetch one email with its full plain-text body."""
        msg = self.service.users().messages().get(
            userId="me",
            id=email_id,
            format="full"
        ).execute()

        email = parse_summary(msg)
        email["body"] = extract_body(msg["payload"])
        return email

    def search(self, text, category="all", limit=10, **filters):
        """Free-text search, across all mail by default."""
        return self.get_emails(category, limit, text=text, **filters)

    def unread_count(self, category=None):
        """Exact number of unread emails in a category.

        resultSizeEstimate is unreliable (caps out around 201), so page
        through matching ids instead — ids only, 500 per request.
        """
        query = build_query(category, unread=True)
        count = 0
        page_token = None

        while True:
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=500,
                pageToken=page_token,
                fields="messages/id,nextPageToken",
            ).execute()

            count += len(results.get("messages", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                return count

    def get_all_categories(self, limit=5):
        """Latest emails from every inbox tab plus Sent."""
        return {
            category: self.get_emails(category, limit)
            for category in ("primary", "promotions", "social", "updates", "sent")
        }

    # ------------------------------------------------------------------
    # Category shortcuts
    # ------------------------------------------------------------------

    def primary(self, limit=10, **filters):
        return self.get_emails("primary", limit, **filters)

    def promotions(self, limit=10, **filters):
        return self.get_emails("promotions", limit, **filters)

    def social(self, limit=10, **filters):
        return self.get_emails("social", limit, **filters)

    def updates(self, limit=10, **filters):
        return self.get_emails("updates", limit, **filters)

    def forums(self, limit=10, **filters):
        return self.get_emails("forums", limit, **filters)

    def purchases(self, limit=10, **filters):
        return self.get_emails("purchases", limit, **filters)

    def inbox(self, limit=10, **filters):
        return self.get_emails("inbox", limit, **filters)

    def starred(self, limit=10, **filters):
        return self.get_emails("starred", limit, **filters)

    def snoozed(self, limit=10, **filters):
        return self.get_emails("snoozed", limit, **filters)

    def sent(self, limit=10, **filters):
        return self.get_emails("sent", limit, **filters)

    def drafts(self, limit=10, **filters):
        return self.get_emails("drafts", limit, **filters)

    def important(self, limit=10, **filters):
        return self.get_emails("important", limit, **filters)

    def spam(self, limit=10, **filters):
        return self.get_emails("spam", limit, **filters)

    def trash(self, limit=10, **filters):
        return self.get_emails("trash", limit, **filters)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_summary(self, email_id):
        # Headers only — much lighter than format="full"
        msg = self.service.users().messages().get(
            userId="me",
            id=email_id,
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()
        return parse_summary(msg)
