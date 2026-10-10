"""Settings loaded from the environment / the project's .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")


def _int_set(value):
    return {int(item) for item in (value or "").split(",") if item.strip()}


# --- LLM -------------------------------------------------------------------
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Secrets (never committed; see .gitignore) -----------------------------
SECRETS_DIR = Path(os.getenv("BUTLER_SECRETS_DIR", ROOT_DIR / "secrets"))

GOOGLE_CLIENT_SECRET_FILE = Path(
    os.getenv("GOOGLE_CLIENT_SECRET_FILE", SECRETS_DIR / "google_client_secret.json")
)
GMAIL_TOKEN_FILE = SECRETS_DIR / "gmail_token.json"
SWIGGY_TOKEN_FILE = SECRETS_DIR / "swiggy_token.json"

# --- Telegram --------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Empty = everyone may use the bot (and read your Gmail)
TELEGRAM_ALLOWED_USER_IDS = _int_set(os.getenv("TELEGRAM_ALLOWED_USER_IDS"))

# Swiggy acts on YOUR account. Set to restrict it to one Telegram user;
# empty = every allowed user gets Swiggy
TELEGRAM_OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID") or 0)
