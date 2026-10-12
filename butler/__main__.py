"""Command-line entry point: `python -m butler <command>`.

Core commands:
    chat        terminal chat
    telegram    run the Telegram bot
    web         run the web UI (http://127.0.0.1:8000)

Integrations add their own, e.g. gmail-login, calendar-login, swiggy-login,
and `gmail` (a quick Gmail reader: `python -m butler gmail updates --unread`).
"""

import asyncio
import sys


def _core_commands():
    def chat():
        from butler.interfaces import cli
        asyncio.run(cli.main())

    def telegram():
        from butler.interfaces import telegram_bot
        telegram_bot.main()

    def web():
        from butler.interfaces import web as web_ui
        web_ui.main()

    return {"chat": chat, "telegram": telegram, "web": web}


def main():
    from butler.config import check_config
    from butler.integrations.registry import cli_commands

    core = _core_commands()
    commands = {**core, **cli_commands()}

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        print("Available commands: " + ", ".join(commands))
        sys.exit(1)

    command = sys.argv.pop(1)
    if command in core:
        check_config(needs_telegram=command == "telegram")
    commands[command]()


if __name__ == "__main__":
    main()
