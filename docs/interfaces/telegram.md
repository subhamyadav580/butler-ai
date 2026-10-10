# Telegram

Chat with Butler from the Telegram app on your phone or desktop. The email picker and approvals become buttons under the message.

## 1. Create your bot

1. In Telegram, open [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Choose a display name, then a username ending in `bot` (for example `my_butler_bot`).
3. BotFather replies with a token like `123456789:AAH...`. Add it to `.env`:

   ```
   TELEGRAM_BOT_TOKEN=123456789:AAH...
   ```

## 2. Start it

```bash
python -m butler telegram
```

Open your bot in Telegram and send `/start`. The reply ends with **your Telegram user ID**; you need it in the next step.

The bot only runs while this command runs. To keep it running all the time, see [Running it permanently](#running-it-permanently).

## 3. Lock it down (important)

Anyone can find a Telegram bot by its username. Without restrictions, **any stranger could read your mail through it**. Add your user ID to `.env`:

```
# Only these Telegram users may use the bot (comma-separated)
TELEGRAM_ALLOWED_USER_IDS=123456789

# Only this user may use Swiggy (which orders on YOUR account)
TELEGRAM_OWNER_ID=123456789
```

Restart the bot. Anyone else now gets "Sorry, you're not allowed to use this bot", along with their own ID, in case you want to add them.

| Setting | Empty means | Set means |
|---|---|---|
| `TELEGRAM_ALLOWED_USER_IDS` | ⚠️ Everyone can use the bot and read your Gmail | Only these users |
| `TELEGRAM_OWNER_ID` | Every allowed user can use your Swiggy account | Only this user gets Swiggy; others still get Gmail and chat |

## Using it

- **Chat:** just type.
- **Email picker:** tap the button for the email you want, type its number, or tap **Cancel**.
- **Approvals:** tap **✅ Approve** or **❌ Reject**, or type `yes` / `no`.
- **Changing your mind:** sending a new message while a question is open cancels the question.
- **`/start`:** shows help and your user ID.
- **`/reset`:** clears this chat's memory.

Each Telegram chat has its own conversation memory.

## Running it permanently

The bot runs as long as the process runs. Some options:

- **A terminal multiplexer:** `tmux new -s butler 'python -m butler telegram'`
- **macOS:** a `launchd` agent. **Linux:** a `systemd` service that runs `/path/to/.venv/bin/python -m butler telegram` with `WorkingDirectory` set to your Butler folder.
- **A small VPS:** copy the project and its `secrets/` folder over, since logins need a browser and are easiest to do on your laptop.

Run only **one** copy of the bot per token. Two copies polling the same bot fail with a `Conflict` error.
