"""Optional password protection for the web UI.

If BUTLER_WEB_PASSWORD is set, logging in returns a token derived from the
password; every API call must send it as `Authorization: Bearer <token>`.
Changing the password invalidates old tokens.
"""

import hashlib
import hmac

from butler.config import WEB_PASSWORD


def auth_required():
    return bool(WEB_PASSWORD)


def _token_for(password):
    return hmac.new(password.encode(), b"butler-web-session", hashlib.sha256).hexdigest()


def check_password(password):
    if not auth_required():
        return True
    return hmac.compare_digest(password.encode(), WEB_PASSWORD.encode())


def issue_token():
    return _token_for(WEB_PASSWORD) if auth_required() else ""


def verify_token(token):
    if not auth_required():
        return True
    return bool(token) and hmac.compare_digest(token, _token_for(WEB_PASSWORD))
