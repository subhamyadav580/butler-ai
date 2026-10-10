"""Command-line entry point.

    python -m butler chat           # terminal chat
    python -m butler telegram       # run the Telegram bot
    python -m butler swiggy-login   # log in to Swiggy (phone + OTP)
    python -m butler gmail [...]    # quick Gmail reader, e.g. `gmail updates --unread`
"""

import asyncio
import sys

COMMANDS = ("chat", "telegram", "swiggy-login", "gmail")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)

    command = sys.argv.pop(1)

    if command == "chat":
        from butler.interfaces import cli
        asyncio.run(cli.main())

    elif command == "telegram":
        from butler.interfaces import telegram_bot
        telegram_bot.main()

    elif command == "swiggy-login":
        from butler.integrations.swiggy import login
        asyncio.run(login.main())

    elif command == "gmail":
        from butler.integrations.gmail.__main__ import main as gmail_main
        gmail_main()


if __name__ == "__main__":
    main()
