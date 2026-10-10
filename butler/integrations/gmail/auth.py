from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import os

from .config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE


def get_gmail_service(credentials_file=CREDENTIALS_FILE, token_file=TOKEN_FILE):
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
