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

## Swiggy

**"Swiggy login has expired"**
Swiggy logins last 5 days and can't be refreshed. Run `python -m butler swiggy-login`.

**Requests fail with `429`**
That's Swiggy's rate limit. Wait a minute and try again.

**Butler searches but never adds anything to the cart**
Smaller models sometimes stall on multi-step flows. Set `OPENAI_MODEL=gpt-4.1-mini` in `.env`, and be explicit: *"Add 1 Classic Paneer Subz Biryani, King Size, no add-ons."*

**The login browser doesn't open, or `Address already in use` (port 8765)**
Another Swiggy login is still running. Close it, or wait for it to time out, and try again.

## Web UI

**The page shows `{"message": "Frontend not built…"}`**
Build it: `cd frontend && npm install && npm run build`, then restart `python -m butler web`.

**`Address already in use` on port 8000**
Something else is using the port. Set `BUTLER_WEB_PORT=8080` in `.env`.

**"Connect" does nothing visible**
The login window opens in a browser **on the machine running Butler**. On a remote server, log in on your laptop instead and copy `secrets/` over.

**Conversations disappeared**
Memory is kept in the running process. Restarting the server, or reconnecting Swiggy (which reloads the agent), clears it.

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
