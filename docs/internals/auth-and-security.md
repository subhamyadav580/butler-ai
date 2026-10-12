# Auth and security

Butler deals with two different questions:

1. **Can Butler act on your accounts?** That's integration auth: the Gmail and Swiggy logins.
2. **Who may use Butler?** That's interface access: the web password and the Telegram allow-list.

## Integration auth

### Gmail: Google OAuth (installed-app flow)

Code: [integrations/gmail/auth.py](../../butler/integrations/gmail/auth.py)

```
secrets/google_client_secret.json  ── your own Google OAuth client ("Desktop app")
            │
python -m butler gmail-login
            │  InstalledAppFlow.run_local_server(): a browser opens on a random localhost port
            ▼
Google consent (scope: gmail.readonly)
            │
            ▼
secrets/gmail_token.json  ── access token + refresh token
```

- **Refreshing:** access tokens are refreshed automatically with the refresh token.
- **Two modes:**
  - `interactive=True` (`gmail-login`, the web Connect button) may open a browser.
  - `interactive=False` (the agent's tools) raises `GmailLoginRequired` instead. A chat in the web UI or Telegram never hangs waiting for a login nobody is watching.
- **Read-only scope:** Butler can't send or delete mail, even if the code had a bug.
- **Testing-mode expiry:** while the Google app is in *Testing* mode, Google expires refresh tokens after about 7 days. Re-login, or publish the app.

### Google Calendar

Same flow as Gmail, through the shared helper [integrations/google_oauth.py](../../butler/integrations/google_oauth.py), with its own token (`secrets/calendar_token.json`) and scope (`calendar.events`: read and edit events). It uses the same `google_client_secret.json`; the Calendar API must be enabled in that Google Cloud project. Creating, changing and deleting events go through `interrupt()` approvals, and the card warns when Google will email guests.

### Swiggy: MCP OAuth 2.1 with PKCE

Code: [integrations/swiggy/auth.py](../../butler/integrations/swiggy/auth.py)

```
python -m butler swiggy-login
   │  MCP SDK OAuthClientProvider:
   │   1. discovers the auth server (/.well-known/oauth-authorization-server)
   │   2. registers a client automatically (POST /auth/register), so no client ID is needed
   │   3. opens the browser with a PKCE challenge
   ▼
Swiggy login: phone number + OTP
   │  redirect → http://localhost:8765/callback  (LocalCallback, a tiny one-shot server)
   ▼
secrets/swiggy_token.json  ── access token, registered client, expires_at
```

- **One login, all services:** the token is issued for `https://mcp.swiggy.com/`, so it covers Food, Instamart and Dineout.
- **Expiry:** tokens last **5 days**, and Swiggy v1 rejects refresh. Butler doesn't try to refresh; it asks you to log in again.
- **Saving tokens:** `FileTokenStorage` saves the token and client, records `expires_at`, and sets the file to `chmod 600`.
- **At startup:** if there's no token, or it has expired, Butler skips Swiggy entirely (`load_swiggy_tools`) and prints one line, instead of failing with an OAuth traceback.
- **During a chat:** if a call fails because the login expired, the tool returns "Swiggy login has expired. Run `swiggy-login`".

### Where secrets live

```
secrets/            ← git-ignored, created by you and by the login commands
├── google_client_secret.json
├── gmail_token.json
└── swiggy_token.json
.env                ← git-ignored: API keys and settings
data/butler.db      ← git-ignored: your saved web chats
```

Treat `secrets/` like a password vault: anyone with these files can read your Gmail and use your Swiggy account.

## Interface access

### Web UI

Code: [web/core/security.py](../../butler/web/core/security.py), [web/dependencies.py](../../butler/web/dependencies.py)

| Setting | Effect |
|---|---|
| `BUTLER_WEB_HOST=127.0.0.1` (default) | Only this computer can connect |
| `BUTLER_WEB_PASSWORD` set | Login screen; every `/api/*` route except `/api/auth/*` and `/api/health` requires `Authorization: Bearer <token>` |

- **The token** is `HMAC-SHA256(password, "butler-web-session")`. It's stateless, and changing the password logs everyone out. Comparisons use `hmac.compare_digest`.
- **The warning:** starting with a public host and no password prints a warning.
- **File serving is locked down:** the frontend server only serves files inside `frontend/dist/`, so requests like `/../.env` get the app page or `404`, never a secret.
- **HTTPS:** Butler doesn't terminate TLS. If you expose it beyond your machine, put HTTPS in front (Caddy, nginx, Cloudflare Tunnel, Tailscale).

### Telegram

Code: [interfaces/telegram_bot.py](../../butler/interfaces/telegram_bot.py)

| Setting | Empty | Set |
|---|---|---|
| `TELEGRAM_ALLOWED_USER_IDS` | Nobody can use the bot (deny by default) | Only these users; others are refused and shown their ID |
| `TELEGRAM_OWNER_ID` | Every allowed user can use Swiggy | Only this user gets Swiggy tools and can approve Swiggy actions. Calendar and todo approvals stay open to every allowed user |

Swiggy access is enforced twice. Users without access never have the Swiggy tools bound to the LLM, and every Swiggy tool also checks `swiggy_allowed` before running. Approve buttons check it too, which matters in group chats.

## Action safety

- **Gmail:** read-only by scope.
- **Calendar:** creating, changing and deleting events always need **Approve**. Guests are only emailed when an event has attendees, and the card says so.
- **Swiggy:** every tool in `NEEDS_APPROVAL` always needs **Approve**: placing or confirming orders (Food, Instamart), booking a table (Dineout), confirming payments, adding or deleting addresses, and clearing carts. Rejecting, ignoring, or moving on never runs them. See [Human in the loop](human-in-the-loop.md).
- **Errors:** tool failures become messages to the LLM, never crashes or partial actions.

## Checklist before sharing your instance

- [ ] `TELEGRAM_ALLOWED_USER_IDS` lists only people you trust (it's empty, meaning nobody, until you add IDs)
- [ ] `TELEGRAM_OWNER_ID` set to yourself (if others use the bot)
- [ ] `BUTLER_WEB_PASSWORD` set and HTTPS in front (if the web UI is reachable from other devices)
- [ ] `secrets/`, `.env`, `data/` not committed (`git status` shows none of them)
