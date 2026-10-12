from butler.config import GOOGLE_CLIENT_SECRET_FILE, SECRETS_DIR

# Read and write events (create/update/delete always need the user's approval)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

CREDENTIALS_FILE = str(GOOGLE_CLIENT_SECRET_FILE)   # same OAuth client as Gmail
TOKEN_FILE = str(SECRETS_DIR / "calendar_token.json")

CALENDAR_ID = "primary"

LOGIN_COMMAND = "python -m butler calendar-login"
