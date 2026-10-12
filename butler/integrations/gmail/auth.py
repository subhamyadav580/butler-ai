from googleapiclient.discovery import build

from butler.integrations.google_oauth import GoogleLoginRequired, get_credentials

from .config import CREDENTIALS_FILE, SCOPES, TOKEN_FILE

LOGIN_COMMAND = "python -m butler gmail-login"


class GmailLoginRequired(GoogleLoginRequired):
    """Gmail isn't connected and we may not open a browser to log in."""


def get_gmail_service(
    credentials_file=CREDENTIALS_FILE,
    token_file=TOKEN_FILE,
    interactive=False,
):
    """Build an authenticated Gmail API client (see google_oauth.get_credentials)."""
    creds = get_credentials(
        scopes=SCOPES,
        token_file=token_file,
        credentials_file=credentials_file,
        interactive=interactive,
        service_name="Gmail",
        login_command=LOGIN_COMMAND,
        error_cls=GmailLoginRequired,
    )
    return build("gmail", "v1", credentials=creds)
