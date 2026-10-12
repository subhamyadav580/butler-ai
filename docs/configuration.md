# Configuration

Butler reads its settings from a `.env` file in the project root. Start from the template:

```bash
cp .env.example .env
```

Real environment variables take priority over `.env`.

## Settings

### Model

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | (required) | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used by the agent. `gpt-4.1-mini` follows multi-step flows (like building a Swiggy cart) more reliably and costs a bit more |

### Web UI

| Variable | Default | Description |
|---|---|---|
| `BUTLER_WEB_HOST` | `127.0.0.1` | Address to listen on. `127.0.0.1` means this computer only; `0.0.0.0` means every network interface |
| `BUTLER_WEB_PORT` | `8000` | Port |
| `BUTLER_WEB_PASSWORD` | (empty: no login) | Require this password in the UI. **Set it whenever the host isn't `127.0.0.1`** |

### Time zone

| Variable | Default | Description |
|---|---|---|
| `BUTLER_TIMEZONE` | (this machine's zone) | IANA name, for example `Asia/Kolkata`. Used for calendar times and "today" or "tomorrow". Set it if Butler runs in a different zone from you |

### Web search

| Variable | Default | Description |
|---|---|---|
| `SERPER_API_KEY` | (empty) | Key from [serper.dev](https://serper.dev). Web search is off when no provider key is set |
| `TAVILY_API_KEY` | (empty) | Key from [tavily.com](https://tavily.com) |
| `TAVILY_SEARCH_DEPTH` | `basic` | `basic` (1 credit) or `advanced` (2 credits, more relevant) |
| `FIRECRAWL_API_KEY` | (empty) | Key from [firecrawl.dev](https://firecrawl.dev) |
| `WEB_SEARCH_PROVIDER` | (first provider with a key) | Default provider to try first: `serper`, `tavily` or `firecrawl`. Others with a key are fallbacks. Choosing **Use first** on the Integrations page overrides it, and providers can be switched off there too |
| `WEB_SEARCH_COUNTRY` | (provider default) | 2-letter country code for localised results: `in`, `us`, `gb`… |

### Swiggy

| Variable | Default | Description |
|---|---|---|
| `SWIGGY_SERVICES` | `food,instamart,dineout` | Which Swiggy services to load. Fewer services means fewer tools for the model |

### Telegram

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | (required for Telegram) | Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_USER_IDS` | (empty: nobody) | Comma-separated Telegram user IDs allowed to use the bot. Send `/start` to the bot to see yours |
| `TELEGRAM_OWNER_ID` | (empty: all allowed users) | The only user who may use Swiggy |

### Paths

| Variable | Default | Description |
|---|---|---|
| `BUTLER_DATA_DIR` | `./data` | Folder for Butler's database (`butler.db`) |
| `BUTLER_DATABASE_PATH` | `<data>/butler.db` | SQLite database: web UI chats, plus todos (shared by all interfaces) |
| `BUTLER_SECRETS_DIR` | `./secrets` | Folder for OAuth clients and tokens |
| `GOOGLE_CLIENT_SECRET_FILE` | `<secrets>/google_client_secret.json` | Your Google OAuth client file |

## Files in `secrets/`

None of these are ever committed; the folder is git-ignored.

| File | Created by | Contains |
|---|---|---|
| `google_client_secret.json` | You download it ([Gmail guide](integrations/gmail.md)) | Your Google OAuth client |
| `gmail_token.json` | `gmail-login` | Gmail access token and refresh token |
| `calendar_token.json` | `calendar-login` | Google Calendar access token and refresh token |
| `swiggy_token.json` | `swiggy-login` | Swiggy access token for all services (lasts 5 days) and registered client |

Back the folder up if you move Butler to another machine. Delete a token file to disconnect that account.

## Example `.env`

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini

TELEGRAM_BOT_TOKEN=123456789:AAH...
TELEGRAM_ALLOWED_USER_IDS=123456789
TELEGRAM_OWNER_ID=123456789

BUTLER_WEB_HOST=127.0.0.1
BUTLER_WEB_PORT=8000
BUTLER_WEB_PASSWORD=
```
