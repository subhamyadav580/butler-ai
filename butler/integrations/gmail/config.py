from butler.config import GOOGLE_CLIENT_SECRET_FILE, SECRETS_DIR

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CREDENTIALS_FILE = str(GOOGLE_CLIENT_SECRET_FILE)

TOKEN_FILE = str(SECRETS_DIR / "gmail_token.json")
