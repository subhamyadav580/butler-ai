# Butler

A personal AI assistant that reads your **Gmail** and orders food on **Swiggy**. You can talk to it from **Telegram** or the terminal.

Butler is a single [LangGraph](https://github.com/langchain-ai/langgraph) agent with tool access. It handles general questions itself, calls the right tools when you ask about your data, and pauses for you whenever a choice or approval is needed.

```
You: how many unread mails in promotions, and what's 15% of 240?
Butler: You have 1,204 unread emails in Promotions. 15% of 240 is 36.

You: open a mail from LinkedIn in updates
Butler: Which email do you want to open?   [1. Your weekly job alerts] [2. …] [Cancel]

You: add 1 Classic Paneer Subz Biryani (King Size) from Behrouz to my cart
Butler: Added to your cart. Item total ₹399, taxes ₹69.85, to pay ₹469. How would you like to pay?
```

## Features

- **Gmail (read-only):** list and search mail by tab or folder (Primary, Promotions, Social, Updates, Sent, Starred, …). You can filter by sender, subject, text, unread, attachments or date, count unread mail, and open a full email.
- **Email picker:** when you ask to open an email, Butler shows a list (with buttons on Telegram) and opens the one you choose.
- **Swiggy Food (via [Swiggy MCP](https://mcp.swiggy.com/builders/)):** saved addresses, restaurant and dish search, menus, cart, coupons, ordering and order tracking.
- **Approval before anything risky:** Butler pauses for Approve/Reject before it places or confirms an order, adds or deletes an address, or clears the cart.
- **Conversation memory:** each Telegram chat has its own conversation, so follow-ups like "who sent that one?" work.
- **Multiple requests in one message:** "check my unread mail and convert 50 USD to INR" works in a single turn.

## How it works

```
Telegram / terminal
        │
        ▼
   ┌─────────┐   tool calls   ┌────────────────────────────────┐
   │  agent  │ ─────────────► │ tools                          │
   │  (LLM)  │ ◄───────────── │  • Gmail (Google API)          │
   └─────────┘    results     │  • Swiggy Food (MCP over HTTP) │
        │                     └───────────────┬────────────────┘
        ▼                                     │ interrupt()
      reply                    pick an email / approve an action
```

- **One agent, every tool:** there's no router. The LLM decides which tools to call, if any.
- **Pausing for your input:** `interrupt()` pauses the graph and the interface (Telegram or terminal) asks you. `Command(resume=…)` continues from exactly where it stopped. Picking an email and approving a Swiggy action both work this way.
- **Memory:** a LangGraph checkpointer saves the conversation per `thread_id`.

## Project structure

```
butler/
├── butler/
│   ├── __main__.py            # `python -m butler <command>`
│   ├── config.py              # settings and secret paths, read from .env
│   ├── agent/
│   │   ├── graph.py           # LangGraph agent: agent ⇄ tools loop, checkpointer
│   │   └── prompts.py         # system prompt and per-integration rules
│   ├── integrations/
│   │   ├── gmail/             # Google OAuth, Gmail client, search queries, LangChain tools
│   │   └── swiggy/            # MCP OAuth (PKCE), MCP client, tool wrappers with approvals
│   └── interfaces/
│       ├── cli.py             # terminal chat
│       └── telegram_bot.py    # Telegram bot with inline buttons
├── secrets/                   # OAuth client and tokens (git-ignored)
├── .env.example
├── pyproject.toml
└── requirements.txt
```

To add a new integration, create `butler/integrations/<name>/` with a `tools.py` that exports LangChain tools. Then add those tools in `agent/graph.py` and their rules in `agent/prompts.py`.

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/<you>/butler.git
cd butler
python -m venv .venv && source .venv/bin/activate
pip install -e .            # or: pip install -r requirements.txt
cp .env.example .env        # then fill it in
```

### 1. OpenAI

Set `OPENAI_API_KEY` in `.env`. You can choose the model with `OPENAI_MODEL`; the default is `gpt-4o-mini`. `gpt-4.1-mini` is noticeably more reliable for multi-step flows such as adding items to the Swiggy cart.

### 2. Gmail

1. In [Google Cloud Console](https://console.cloud.google.com/), enable the **Gmail API**.
2. Create an **OAuth client ID** of type *Desktop app* and download the JSON.
3. Save it as `secrets/google_client_secret.json`.
4. Run `python -m butler gmail`. A browser opens for Google login, and the token is saved to `secrets/gmail_token.json`.

### 3. Swiggy (optional)

```bash
python -m butler swiggy-login
```

A browser opens for Swiggy's phone and OTP login. The token is saved to `secrets/swiggy_token.json`. On `http://localhost`, this works for personal use without Swiggy's approval; see [Swiggy's access docs](https://mcp.swiggy.com/builders/docs/operate/access/) for production access.

> Swiggy tokens last **5 days**, and Swiggy v1 doesn't support refreshing them. Run `swiggy-login` again when Butler says the login has expired.

If you skip this step, Butler runs without Swiggy.

### 4. Telegram (optional)

1. Create a bot with [@BotFather](https://t.me/BotFather) and set `TELEGRAM_BOT_TOKEN`.
2. Start the bot and send it `/start`. It replies with your Telegram user ID.
3. Put that ID in `TELEGRAM_ALLOWED_USER_IDS` (and in `TELEGRAM_OWNER_ID` to keep Swiggy to yourself), then restart the bot.

## Usage

```bash
python -m butler chat           # terminal chat
python -m butler telegram       # Telegram bot
python -m butler swiggy-login   # (re)login to Swiggy
python -m butler gmail updates --from linkedin --unread   # quick Gmail reader
```

If you installed it with `pip install -e .`, you can run `butler chat`, `butler telegram`, and so on directly.

Telegram commands: `/start` shows help and your user ID; `/reset` clears that chat's memory.

## Security

Butler acts on **your** accounts. Before you share the bot:

- **Lock the bot down.** With `TELEGRAM_ALLOWED_USER_IDS` empty, anyone who finds the bot can read your Gmail.
- **Lock Swiggy down.** With `TELEGRAM_OWNER_ID` empty, every allowed user can order on your Swiggy account (each order still needs an Approve tap).
- **Keep secrets out of git.** Everything in `secrets/` and `.env` is git-ignored. Never commit them.

## Limitations

- **Memory is in-process:** restarting clears every conversation. Swap `InMemorySaver` for a SQLite or Postgres checkpointer to keep it.
- **Gmail is read-only:** no sending, labelling or deleting.
- **Swiggy:** India only, Food only for now (Instamart, Dineout and Scenes are available on the same MCP server). Cash on delivery is the simplest way to pay.
