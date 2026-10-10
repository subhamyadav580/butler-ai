from .categories import OUTGOING_CATEGORIES


def print_emails(emails, category=None):
    for email in emails:
        print("=" * 60)
        if category in OUTGOING_CATEGORIES:
            print("To:", email["to"])
        else:
            print("From:", email["from"])
        print("Subject:", email["subject"])
        print("Date:", email["date"])
        print("Message:", email["snippet"])
