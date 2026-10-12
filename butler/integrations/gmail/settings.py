"""The "Allow replying & sending" switch, stored in data/butler.db.

Shared by the web server and the Telegram bot, so flipping it on the web UI
applies everywhere immediately, without a restart.
"""

from butler.db import get_settings

from .config import ALLOW_SEND_DEFAULT

SETTINGS_KEY = "gmail"


def send_enabled() -> bool:
    return bool(get_settings().get(SETTINGS_KEY, {}).get("send_enabled", ALLOW_SEND_DEFAULT))


def set_send_enabled(enabled: bool):
    current = get_settings().get(SETTINGS_KEY, {}) or {}
    get_settings().set(SETTINGS_KEY, {**current, "send_enabled": bool(enabled)})
