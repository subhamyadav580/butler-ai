import argparse

from .categories import CATEGORIES, DEFAULT_CATEGORY
from .client import Gmail
from .printer import print_emails


def main():
    parser = argparse.ArgumentParser(description="Read Gmail by category")
    parser.add_argument(
        "category",
        nargs="?",
        default=DEFAULT_CATEGORY,
        choices=list(CATEGORIES),
    )
    parser.add_argument("-n", "--limit", type=int, default=5)
    parser.add_argument("--from", dest="sender")
    parser.add_argument("--to")
    parser.add_argument("--subject")
    parser.add_argument("--text", help="free-text search")
    parser.add_argument("--unread", action="store_true", default=None)
    parser.add_argument("--attachment", action="store_true")
    parser.add_argument("--after", help="YYYY/MM/DD")
    parser.add_argument("--before", help="YYYY/MM/DD")
    args = parser.parse_args()

    emails = Gmail(interactive=True).get_emails(
        args.category,
        args.limit,
        sender=args.sender,
        to=args.to,
        subject=args.subject,
        text=args.text,
        unread=args.unread,
        has_attachment=args.attachment,
        after=args.after,
        before=args.before,
    )

    print(f"# {args.category.upper()} ({len(emails)})")
    print_emails(emails, args.category)


if __name__ == "__main__":
    main()
