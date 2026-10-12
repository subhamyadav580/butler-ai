from googleapiclient.discovery import build

from butler.integrations.google_oauth import GoogleLoginRequired, get_credentials

from .config import CREDENTIALS_FILE, SCOPES, SEND_SCOPES, TOKEN_FILE

LOGIN_COMMAND = "python -m butler gmail-login"


class GmailLoginRequired(GoogleLoginRequired):
    """Gmail isn't connected (or lacks a permission) and we may not open a browser."""


def get_gmail_service(
    credentials_file=CREDENTIALS_FILE,
    token_file=TOKEN_FILE,
    interactive=False,
    send=False,
    force_login=False,
):
    """Build an authenticated Gmail API client (see google_oauth.get_credentials).

    send=True needs the compose permission (drafts + sending). Logins ask for
    it whenever sending is switched on, so one login covers both.
    """
    from .settings import send_enabled   # local: settings touch the database

    creds = get_credentials(
        scopes=SEND_SCOPES if send else SCOPES,
        login_scopes=SEND_SCOPES if (send or send_enabled()) else SCOPES,
        token_file=token_file,
        credentials_file=credentials_file,
        interactive=interactive,
        service_name="Gmail",
        login_command=LOGIN_COMMAND,
        error_cls=GmailLoginRequired,
        force_login=force_login,
    )
    return build("gmail", "v1", credentials=creds)
