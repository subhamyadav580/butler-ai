"""Log in to Gmail (Google OAuth in the browser) and save the token.

Run from the project root:
    python -m butler gmail-login
"""

from .auth import GmailLoginRequired


def main():
    try:
        from .auth import get_gmail_service
        service = get_gmail_service(interactive=True, force_login=True)
        profile = service.users().getProfile(userId="me").execute()
    except GmailLoginRequired as error:
        raise SystemExit(str(error)) from error
    print(f"Gmail connected: {profile['emailAddress']}")


if __name__ == "__main__":
    main()
