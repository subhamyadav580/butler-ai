from butler.config import CALENDAR_TOKEN_FILE, GOOGLE_CLIENT_SECRET_FILE

# Read and write events (create/update/delete always need the user's approval)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

CREDENTIALS_FILE = str(GOOGLE_CLIENT_SECRET_FILE)   # same OAuth client as Gmail
TOKEN_FILE = str(CALENDAR_TOKEN_FILE)

CALENDAR_ID = "primary"

LOGIN_COMMAND = "python -m butler calendar-login"
