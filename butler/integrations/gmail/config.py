from butler.config import GMAIL_TOKEN_FILE, GOOGLE_CLIENT_SECRET_FILE

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CREDENTIALS_FILE = str(GOOGLE_CLIENT_SECRET_FILE)

TOKEN_FILE = str(GMAIL_TOKEN_FILE)
