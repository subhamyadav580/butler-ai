from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import os

from .config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE

LOGIN_COMMAND = "python -m butler gmail-login"


class GmailLoginRequired(Exception):
    """Gmail isn't connected and we may not open a browser to log in."""


def get_gmail_service(
    credentials_file=CREDENTIALS_FILE,
    token_file=TOKEN_FILE,
    interactive=False,
):
    """Build an authenticated Gmail API client.

    interactive=True may open a browser for the Google login (CLI / connect
    button). interactive=False (the agent) raises GmailLoginRequired instead,
    so a chat never hangs waiting for a login nobody is watching.
    """
    creds = None

    # Load previously generated OAuth token
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(
            token_file,
            SCOPES
        )

    # If credentials don't exist or are invalid
    if not creds or not creds.valid:

        # Refresh expired token
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # First-time OAuth login
        else:
            if not interactive:
                raise GmailLoginRequired(
                    f"Gmail is not connected. Run `{LOGIN_COMMAND}` or use "
                    "Connect on the web UI's Integrations page."
                )
            if not os.path.exists(credentials_file):
                raise GmailLoginRequired(
                    "Google OAuth client file not found at "
                    f"{credentials_file}. See the README's Gmail setup."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file,
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # Save OAuth token
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build(
        "gmail",
        "v1",
        credentials=creds
    )
