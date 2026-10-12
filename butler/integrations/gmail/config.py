import os

from butler.config import GOOGLE_CLIENT_SECRET_FILE, SECRETS_DIR

READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
# Create drafts and send mail. Only requested once sending is switched on.
COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"

SCOPES = [READ_SCOPE]                        # what reading needs
SEND_SCOPES = [READ_SCOPE, COMPOSE_SCOPE]    # what replying/sending/drafts need

CREDENTIALS_FILE = str(GOOGLE_CLIENT_SECRET_FILE)

TOKEN_FILE = str(SECRETS_DIR / "gmail_token.json")

# Default for the "Allow replying & sending" switch (the web UI's Gmail card
# overrides it). Off: Butler can only read mail.
ALLOW_SEND_DEFAULT = os.getenv("GMAIL_ALLOW_SEND", "false").strip().lower() in ("1", "true", "yes", "on")
