"""Log in to Google Calendar (Google login in the browser) and save the token.

Run from the project root:
    python -m butler calendar-login

Uses the same Google OAuth client as Gmail (secrets/google_client_secret.json).
The Google Calendar API must be enabled in that Google Cloud project.
"""

from googleapiclient.errors import HttpError

from .auth import CalendarLoginRequired
from .client import Calendar


def main():
    try:
        from .auth import get_calendar_service
        get_calendar_service(interactive=True, force_login=True)   # fresh login
        profile = Calendar().profile()
    except CalendarLoginRequired as error:
        raise SystemExit(str(error)) from error
    except HttpError as error:
        text = str(error)
        if error.resp.status == 403 and ("accessNotConfigured" in text or "has not been used" in text):
            raise SystemExit(
                "Logged in, but the Google Calendar API is not enabled for your "
                "Google Cloud project. Enable it at "
                "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com "
                "then run this again."
            ) from error
        raise
    print(f"Google Calendar connected: {profile['calendar']} (time zone {profile['timeZone']})")


if __name__ == "__main__":
    main()
