"""Settings loaded from the environment / the project's .env file."""

import os
from datetime import datetime
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
CALENDAR_TOKEN_FILE = SECRETS_DIR / "calendar_token.json"
SWIGGY_TOKEN_FILE = SECRETS_DIR / "swiggy_token.json"

# --- Telegram --------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Only these Telegram user IDs may use the bot. Empty = nobody (deny by default)
TELEGRAM_ALLOWED_USER_IDS = _int_set(os.getenv("TELEGRAM_ALLOWED_USER_IDS"))

# Swiggy acts on YOUR account. Set to restrict it to one Telegram user;
# empty = every allowed user gets Swiggy
TELEGRAM_OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID") or 0)

# --- Time zone ---------------------------------------------------------------
# IANA name like "Asia/Kolkata". Empty = this machine's local time zone.
TIMEZONE = os.getenv("BUTLER_TIMEZONE", "")


def local_tz():
    """The user's time zone: BUTLER_TIMEZONE, else the machine's local zone."""
    if TIMEZONE:
        from zoneinfo import ZoneInfo
        return ZoneInfo(TIMEZONE)
    return datetime.now().astimezone().tzinfo


# --- Swiggy ------------------------------------------------------------------
# Which Swiggy services to load. Fewer services = fewer tools for the LLM to
# choose from, which helps smaller models pick the right one.
SWIGGY_SERVICES = {
    s.strip().lower()
    for s in os.getenv("SWIGGY_SERVICES", "food,instamart,dineout").split(",")
    if s.strip()
}

# --- Web UI ----------------------------------------------------------------
# Defaults to localhost only: the UI can read your Gmail and order on Swiggy
WEB_HOST = os.getenv("BUTLER_WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("BUTLER_WEB_PORT", "8000"))

# Set to require a password in the web UI. Empty = no login (fine on localhost)
WEB_PASSWORD = os.getenv("BUTLER_WEB_PASSWORD", "")

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

# --- Storage -----------------------------------------------------------------
# Web UI chat list + transcripts (SQLite). Agent memory stays in RAM.
DATA_DIR = Path(os.getenv("BUTLER_DATA_DIR", ROOT_DIR / "data"))
DATABASE_PATH = Path(os.getenv("BUTLER_DATABASE_PATH", DATA_DIR / "butler.db"))


def check_config(needs_telegram=False):
    """Fail fast with a readable message instead of a traceback."""
    problems = []
    if not os.getenv("OPENAI_API_KEY"):
        problems.append("OPENAI_API_KEY is not set. Add it to .env (see .env.example).")
    if needs_telegram and not TELEGRAM_BOT_TOKEN:
        problems.append("TELEGRAM_BOT_TOKEN is not set. Create a bot with @BotFather and add it to .env.")
    if problems:
        raise SystemExit("Butler can't start:\n  - " + "\n  - ".join(problems))
