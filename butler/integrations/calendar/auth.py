from googleapiclient.discovery import build

from butler.integrations.google_oauth import GoogleLoginRequired, get_credentials

from .config import CREDENTIALS_FILE, LOGIN_COMMAND, SCOPES, TOKEN_FILE


class CalendarLoginRequired(GoogleLoginRequired):
    """Calendar isn't connected and we may not open a browser to log in."""


def get_calendar_service(interactive=False):
    """Build an authenticated Google Calendar API client."""
    creds = get_credentials(
        scopes=SCOPES,
        token_file=TOKEN_FILE,
        credentials_file=CREDENTIALS_FILE,
        interactive=interactive,
        service_name="Google Calendar",
        login_command=LOGIN_COMMAND,
        error_cls=CalendarLoginRequired,
    )
    return build("calendar", "v3", credentials=creds)
