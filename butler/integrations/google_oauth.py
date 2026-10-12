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
    login_scopes=None,
    force_login=False,
):
    """Load, refresh or (if interactive) create Google credentials.

    scopes: what this call needs. The saved token must have granted all of
    them; a token from an earlier, narrower login (e.g. read-only Gmail when
    sending is now needed) counts as "needs a new login".
    login_scopes: what to ask for if a new login happens (defaults to scopes).
    Lets a read-only call keep working while logins ask for more.
    force_login: always open a fresh login (interactive only). The web UI's
    Reconnect and the `*-login` commands use it.

    interactive=True may open a browser for the Google login (CLI login
    commands, the web UI's Connect button). interactive=False (the agent's
    tools) raises `error_cls` instead, so a chat never hangs waiting for a
    login nobody is watching.
    """
    how_to_connect = (
        f"Run `{login_command}` or use Connect on the web UI's Integrations page."
    )

    login_scopes = login_scopes or scopes

    creds = None
    if interactive and force_login:
        pass                                    # skip the saved token: log in again
    elif os.path.exists(token_file):
        # Load with the scopes the token was actually granted, not the ones we
        # want: forcing new scopes onto an old token only fails later with a 403
        creds = Credentials.from_authorized_user_file(token_file)
        # Interactive logins also re-login when the token lacks access that's now
        # wanted (e.g. sending was switched on after a read-only login)
        if not creds.has_scopes(scopes if not interactive else login_scopes):
            if not interactive:
                raise error_cls(
                    f"{service_name} needs more permission for this. Reconnect it "
                    f"(Integrations page, or `{login_command}`) and allow the new access."
                )
            creds = None    # log in again with the wider scopes

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
                raise error_cls(f"{service_name} login has expired. {how_to_connect}") from None

    if not interactive:
        raise error_cls(f"{service_name} is not connected. {how_to_connect}")

    if not os.path.exists(credentials_file):
        raise error_cls(
            f"Google OAuth client file not found at {credentials_file}. "
            "See docs/integrations/gmail.md for the one-time Google setup."
        )

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, login_scopes)
    creds = flow.run_local_server(port=0)
    _save(token_file, creds)
    return creds


def _save(token_file, creds):
    with open(token_file, "w") as token:
        token.write(creds.to_json())
    os.chmod(token_file, 0o600)


def google_status(token_file, scopes, client_file, service_name, wanted_scopes=None, wanted_reason=""):
    """Integrations-page status for a Google integration (quick: no network).

    wanted_scopes: extra access an enabled option needs (e.g. Gmail sending);
    if the token lacks it, the status says to Reconnect.
    """
    if not os.path.exists(client_file):
        return {
            "state": "needs_setup",
            "detail": (
                "Create a Google OAuth client (Desktop app) and save it as "
                f"{os.path.basename(client_file)} in the secrets/ folder. "
                "See docs/integrations/gmail.md."
            ),
        }
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file)
        if (creds.valid or creds.refresh_token) and creds.has_scopes(scopes):
            if wanted_scopes and not creds.has_scopes(wanted_scopes):
                return {"state": "connected",
                        "detail": f"Connected (read-only). {wanted_reason} Click Reconnect and allow the new access."}
            return {"state": "connected", "detail": "Connected."}
    return {"state": "disconnected", "detail": f"{service_name} is not connected yet."}
