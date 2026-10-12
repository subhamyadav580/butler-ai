# Troubleshooting

## Starting up

**`Butler can't start: OPENAI_API_KEY is not set`**
Add your key to `.env` (`OPENAI_API_KEY=sk-...`), or export it in your shell.

**`Butler can't start: TELEGRAM_BOT_TOKEN is not set`**
Only `python -m butler telegram` needs it. Get one from [@BotFather](https://t.me/BotFather). See the [Telegram guide](interfaces/telegram.md).

**`No module named butler`, or the `butler` command isn't found**
Activate the virtual environment (`source .venv/bin/activate`) and run commands from the project root. If it still fails, run `pip install -e .` again.

**`WARNING: Swiggy not connected … Continuing without Swiggy.`**
This isn't an error. Butler works without Swiggy. Run `python -m butler swiggy-login` to add it.

## Gmail

**Butler says Gmail isn't connected**
Run `python -m butler gmail-login`. If it says the OAuth client file isn't found, do the one-time setup in the [Gmail guide](integrations/gmail.md) and save the file as `secrets/google_client_secret.json`.

**`Error 403: access_denied` in the browser during login**
Your Google account isn't a **test user** of your Google Cloud app. Add it under *OAuth consent screen → Audience → Test users*.

**"Google hasn't verified this app"**
That's expected: it's your own app. Click **Continue**.

**Gmail worked for a week, then fails with `invalid_grant`**
Apps in Google's *Testing* mode get logins that expire after about 7 days. Run `python -m butler gmail-login` again, or publish the app (see the [Gmail guide](integrations/gmail.md#good-to-know)).

## Todos

**Todos added on Telegram don't show on the Todos page**
The page refreshes when you return to the tab. Click another tab and back, or reload. Both processes must point to the same `data/butler.db` (the same `BUTLER_DATABASE_PATH`).

**"remind me…" didn't notify me**
Butler doesn't send notifications yet. Ask it to also put the reminder on your Google Calendar, which can alert you.

## Google Calendar

**`calendar-login` says the Google Calendar API is not enabled**
Enable it in the same Google Cloud project as your OAuth client: [Google Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com) → **Enable**. Then run `python -m butler calendar-login` again.

**Times are off by a few hours**
Butler is using a different time zone from you, which is common on servers. Set `BUTLER_TIMEZONE=Asia/Kolkata` (your zone) in `.env` and restart.

**"Google Calendar login has expired"**
Same 7-day Testing-mode limit as Gmail. Run `python -m butler calendar-login`, or publish your Google app.

**An event from a shared or secondary calendar is missing**
Butler only reads your primary calendar for now.

## Swiggy

**"Swiggy login has expired"**
Swiggy logins last 5 days and can't be refreshed. Run `python -m butler swiggy-login`.

**Requests fail with `429`**
That's Swiggy's rate limit. Wait a minute and try again.

**`WARNING: Swiggy instamart unavailable (… 429 …)` at startup, or a service is "not loaded right now"**
Swiggy rate-limited that service while Butler started. The other services still work. Wait a minute, then restart Butler or click **Reload agent** on the Integrations page.

**Instamart says the address isn't serviceable**
Instamart doesn't deliver everywhere. Ask Butler to use another saved address.

**Dineout: "paid deal", or it won't book**
Paid prebook deals need UPI payment in the Swiggy app. Choose a free slot, or book the paid deal in the app. Cancelling a booking also has to happen in the app.

**Butler invents IDs, picks the wrong address, or keeps asking "would you like…?"**
The model is struggling with many tools and multi-step flows. Set `OPENAI_MODEL=gpt-4.1-mini`, or load fewer Swiggy services with `SWIGGY_SERVICES=food`.

**Butler searches but never adds anything to the cart**
Smaller models sometimes stall on multi-step flows. Set `OPENAI_MODEL=gpt-4.1-mini` in `.env`, and be explicit: *"Add 1 Classic Paneer Subz Biryani, King Size, no add-ons."*

**Instamart items disappeared from the cart**
Instamart replaces the whole cart on every update. Butler is instructed to re-send existing items; if a model skipped that, ask it to add them again, and consider `gpt-4.1-mini`.

**The login browser doesn't open, or `Address already in use` (port 8765)**
Another Swiggy login is still running. Close it, or wait for it to time out, and try again.

## Web UI

**The page shows `{"message": "Frontend not built…"}`**
Build it: `cd frontend && npm install && npm run build`, then restart `python -m butler web`.

**`Address already in use` on port 8000**
Something else is using the port. Set `BUTLER_WEB_PORT=8080` in `.env`.

**"Connect" does nothing visible**
The login window opens in a browser **on the machine running Butler**. On a remote server, log in on your laptop instead and copy `secrets/` over.

**Butler forgot what we talked about after a restart**
Expected. Your chats and their messages are saved (`data/butler.db`), but Butler's working memory is kept in the running process. Restarting, or reconnecting Swiggy (which reloads the agent), clears it, so Butler continues an old chat from your next message.

## Telegram

**The bot doesn't reply at all**
Check that `python -m butler telegram` is still running, and that only **one** copy is running. Two copies with the same token cause `Conflict: terminated by other getUpdates request`.

**"Sorry, you're not allowed to use this bot"**
Your user ID isn't in `TELEGRAM_ALLOWED_USER_IDS`. The message shows your ID; add it and restart.

**Swiggy doesn't work on Telegram, but does in the web UI**
`TELEGRAM_OWNER_ID` is set to someone else's ID. Set it to yours, or leave it empty.

**"Sorry, something went wrong"**
The full error is in the terminal running the bot. Send `/reset` to start a fresh conversation.

## Still stuck?

Open an issue with the command you ran, the full error from the terminal, and your OS and Python version. Remove any tokens or keys first.
