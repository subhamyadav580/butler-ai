"""Shared Google OAuth (installed-app flow) for Gmail, Calendar, …

Each Google integration keeps its own token file and scopes, but they all
use the same OAuth client (secrets/google_client_secret.json).
"""

import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


class GoogleLoginRequired(Exception):
    """Not connected (or the login expired) and we may not open a browser."""


def get_credentials(
    *,
    scopes,
    token_file,
    credentials_file,
    interactive,
    service_name,
    login_command,
    error_cls=GoogleLoginRequired,
):
    """Load, refresh or (if interactive) create Google credentials.

    interactive=True may open a browser for the Google login (CLI login
    commands, the web UI's Connect button). interactive=False (the agent's
    tools) raises `error_cls` instead, so a chat never hangs waiting for a
    login nobody is watching.
    """
    how_to_connect = (
        f"Run `{login_command}` or use Connect on the web UI's Integrations page."
    )

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save(token_file, creds)
            return creds
        except RefreshError:
            # e.g. invalid_grant: apps in Google's "Testing" mode get
            # refresh tokens that expire after ~7 days
            if not interactive:
                raise error_cls(f"{service_name} login has expired. {how_to_connect}")

    if not interactive:
        raise error_cls(f"{service_name} is not connected. {how_to_connect}")

    if not os.path.exists(credentials_file):
        raise error_cls(
            f"Google OAuth client file not found at {credentials_file}. "
            "See docs/integrations/gmail.md for the one-time Google setup."
        )

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
    creds = flow.run_local_server(port=0)
    _save(token_file, creds)
    return creds


def _save(token_file, creds):
    with open(token_file, "w") as token:
        token.write(creds.to_json())
    os.chmod(token_file, 0o600)
