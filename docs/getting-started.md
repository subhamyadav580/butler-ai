# Getting started

This guide takes you from nothing to a working assistant. It takes about **15 minutes**, most of it on the one-time Google setup.

Each step is useful on its own, so you can stop after any of them.

| Step | What you get | Time |
|---|---|---|
| [1. Install](#1-install) | Butler on your machine | 3 min |
| [2. Add your OpenAI key](#2-add-your-openai-key) | A working chat for general questions | 1 min |
| [3. Connect Gmail](#3-connect-gmail) | "How many unread mails…", "open the mail from…" | 8 min |
| [4. Connect Swiggy](#4-connect-swiggy-optional) | Food delivery, Instamart groceries, Dineout tables (India) | 1 min |
| [5. Pick an interface](#5-pick-an-interface) | Web UI, Telegram, or terminal | 2 min |

## Before you start

You need:

- **Python 3.11 or newer.** Check with `python3 --version`.
- **An OpenAI API key** from [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Butler uses `gpt-4o-mini` by default, which costs a fraction of a cent per message.
- **Node.js 20 or newer**, only for the web UI. Check with `node --version`.
- **A Google account**, for Gmail.
- **A Swiggy account and an Indian phone number**, for Swiggy.

## 1. Install

```bash
git clone https://github.com/<your-username>/butler-ai.git
cd butler-ai

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
```

Check it worked:

```bash
python -m butler
```

You should see the list of commands.

> Every later command assumes the virtual environment is active (your prompt starts with `(.venv)`). If you open a new terminal, run `source .venv/bin/activate` again.

## 2. Add your OpenAI key

```bash
cp .env.example .env
```

Open `.env` and fill in the key:

```
OPENAI_API_KEY=sk-...your key...
```

Then try it:

```bash
python -m butler chat
```

```
You: What's 18% of 2,450?
AI: 18% of 2,450 is 441.
```

Type `exit` to quit. Butler now works for general questions. If you ask about mail, it tells you Gmail isn't connected yet; that's expected.

## 3. Connect Gmail

Google needs you to register Butler as your own "app" once. This is free and takes about 8 minutes. Follow **[the Gmail guide](integrations/gmail.md)**, then run:

```bash
python -m butler gmail-login
```

A browser opens. Sign in, allow read-only access, and you'll see:

```
Gmail connected: you@gmail.com
```

## 4. Connect Swiggy (optional)

No setup is needed. Just log in:

```bash
python -m butler swiggy-login
```

A browser opens. Enter your phone number and the OTP. The terminal then lists Swiggy's tools and your saved addresses.

Swiggy logins expire after **5 days**; run the command again when Butler tells you. See **[the Swiggy guide](integrations/swiggy.md)**.

## 5. Pick an interface

### Web UI

```bash
cd frontend && npm install && npm run build && cd ..   # once
python -m butler web
```

Open **http://127.0.0.1:8000**. The **Integrations** page shows what's connected and lets you connect Gmail and Swiggy from the browser. See [the web UI guide](interfaces/web.md).

### Telegram

1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token.
2. Add it to `.env`: `TELEGRAM_BOT_TOKEN=123456:ABC...`
3. Run `python -m butler telegram`, open your bot in Telegram, and send `/start`.
4. Lock the bot down to yourself. This matters: it can read your mail. See [the Telegram guide](interfaces/telegram.md).

### Terminal

```bash
python -m butler chat
```

See [the terminal guide](interfaces/cli.md).

## What to try

```
How many unread mails do I have in Promotions?
Show my latest 5 mails from LinkedIn in Updates
Open a mail from Amazon                          ← shows a picker
Any mail with attachments from last week?
Which addresses do I have saved on Swiggy?
Find veg biryani near my Office                  ← uses your saved address
Add 1 of the first one to my cart
Place the order, cash on delivery                ← asks you to Approve
Search Instamart for milk and bread              ← groceries
Find Italian restaurants in Connaught Place      ← Dineout
Book a free table for 2 tomorrow at 8 pm         ← asks you to Approve
```

## Next steps

- **[Configuration](configuration.md):** change the model, port, password and more
- **[Troubleshooting](troubleshooting.md):** if something doesn't work
- **[Architecture](architecture.md):** how it works, and how to add an integration
