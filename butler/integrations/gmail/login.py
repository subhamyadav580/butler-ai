"""Log in to Gmail (Google OAuth in the browser) and save the token.

Run from the project root:
    python -m butler gmail-login
"""

from .auth import GmailLoginRequired
from .client import Gmail


def main():
    try:
        gmail = Gmail(interactive=True)
        profile = gmail.service.users().getProfile(userId="me").execute()
    except GmailLoginRequired as error:
        raise SystemExit(str(error)) from error
    print(f"Gmail connected: {profile['emailAddress']}")


if __name__ == "__main__":
    main()
