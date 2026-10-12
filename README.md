# Butler

**A self-hosted personal AI assistant for your Gmail, Google Calendar, todos and Swiggy (Food, Instamart, Dineout).** You can chat with it in a **web UI**, on **Telegram**, or in your **terminal**.

```
You:    how many unread mails in Promotions, and what's 15% of 240?
Butler: You have 1,204 unread emails in Promotions. 15% of 240 is 36.

You:    open a mail from LinkedIn
Butler: Which email do you want to open?   [Your weekly job alerts] [Cancel]

You:    remind me to pay rent on Friday, it's important
Butler: Added "Pay rent", due Fri 16 Oct, high priority. Want me to put it on your calendar too?

You:    block 30 min for a call with priya@example.com on Friday at 4 pm
Butler: ⚠️ Add this event to your Google Calendar?  Fri 16 Oct, 4:00–4:30 PM · invites priya@example.com   [Approve] [Reject]

You:    add 1 veg biryani from Behrouz to my cart
Butler: Added. Item total ₹399 · taxes ₹69.85 · to pay ₹469. How would you like to pay?

You:    book a free table for 2 at Brewtally Honest tomorrow at 7 pm
Butler: ⚠️ Book this table on Swiggy Dineout?  Guests: 2 · Sun 11 Oct, 7:00 PM   [Approve] [Reject]
```

Butler is open source and runs on your own machine. You connect **your own** accounts, and your tokens stay in a local `secrets/` folder.

## What it can do

| | |
|---|---|
| 📬 **Gmail** (read-only) | List, search and filter mail by tab (Primary, Promotions, Updates, …), sender, subject, date or unread; count unread mail; open any email |
| 📅 **Google Calendar** | See your schedule, find free time, add, move or cancel events (with Meet links and guests) |
| ☑️ **Todos** | Butler's own todo list: due dates, lists, priorities; a Todos page in the web UI. No setup |
| 🍔 **Swiggy Food** (India) | Restaurant and dish search, menus, cart, coupons, ordering, order tracking |
| 🛒 **Swiggy Instamart** (India) | Groceries and essentials: product search, your usual items, cart, checkout, tracking |
| 🍽️ **Swiggy Dineout** (India) | Find restaurants, check available tables, book free reservations |
| 💬 **General questions** | Anything else, answered directly by the model |
| ✋ **Asks before acting** | Shows a picker when you want to open an email, and asks you to **Approve/Reject** before placing an order, booking a table, or changing your account |

## Three ways to use it

All three use the same agent, so pick whichever you like, or run several at once.

| Interface | Start it with | Best for |
|---|---|---|
| 🌐 **Web UI** | `python -m butler web` → open http://127.0.0.1:8000 | Day-to-day use on your computer; connecting accounts |
| ✈️ **Telegram** | `python -m butler telegram` | Using Butler from your phone, anywhere |
| ⌨️ **Terminal** | `python -m butler chat` | Quick questions, scripting, debugging |

## Quick start

You need **Python 3.11+**, an **OpenAI API key**, and **Node 20+** if you want the web UI.

```bash
# 1. Get the code and install it
git clone https://github.com/<your-username>/butler-ai.git
cd butler-ai
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .

# 2. Configure: add your OpenAI key to .env
cp .env.example .env

# 3. Try it
python -m butler chat
```

Butler already answers general questions at this point. To give it your mail and food ordering, connect your accounts:

| Integration | How to connect | Guide |
|---|---|---|
| Gmail | Create a Google OAuth client once, then `python -m butler gmail-login` | [docs/integrations/gmail.md](docs/integrations/gmail.md) |
| Google Calendar | Same Google client + enable the Calendar API, then `python -m butler calendar-login` | [docs/integrations/calendar.md](docs/integrations/calendar.md) |
| Todos | Nothing to set up | [docs/integrations/todos.md](docs/integrations/todos.md) |
| Swiggy | `python -m butler swiggy-login` (phone number + OTP) | [docs/integrations/swiggy.md](docs/integrations/swiggy.md) |

You can also connect them from the **Integrations** page of the web UI.

The full walkthrough is in **[Getting started](docs/getting-started.md)**.

## Documentation

- **[Getting started](docs/getting-started.md):** from zero to a working assistant, step by step
- **Interfaces:** [Web UI](docs/interfaces/web.md) · [Telegram](docs/interfaces/telegram.md) · [Terminal](docs/interfaces/cli.md)
- **Integrations:** [Gmail](docs/integrations/gmail.md) · [Google Calendar](docs/integrations/calendar.md) · [Todos](docs/integrations/todos.md) · [Swiggy](docs/integrations/swiggy.md)
- **[Configuration](docs/configuration.md):** every `.env` setting
- **[Troubleshooting](docs/troubleshooting.md):** common problems and fixes
- **[Architecture](docs/architecture.md):** the overview of how it works
- **[How Butler works (internals)](docs/internals/README.md):** [memory](docs/internals/memory.md) · [the agent](docs/internals/agent.md) · [tools](docs/internals/tools.md) · [adding tools](docs/internals/adding-tools.md) · [human in the loop](docs/internals/human-in-the-loop.md) · [streaming](docs/internals/streaming.md) · [auth and security](docs/internals/auth-and-security.md) · [request lifecycle](docs/internals/request-lifecycle.md)

## Commands

```bash
python -m butler web            # web UI
python -m butler telegram       # Telegram bot
python -m butler chat           # terminal chat
python -m butler gmail-login    # connect Gmail
python -m butler calendar-login # connect Google Calendar
python -m butler swiggy-login   # connect Swiggy (again every 5 days)
python -m butler gmail updates --from linkedin --unread   # quick Gmail reader, no AI
```

After `pip install -e .` you can also write `butler web`, `butler chat`, and so on.

## Security

Butler acts on **your** accounts, so treat it like a password manager:

- **Secrets stay local.** `.env`, `secrets/` and `data/` (your saved chats and todos) are git-ignored and never leave your machine.
- **The web UI is local by default.** It only listens on `127.0.0.1`. If you expose it, set `BUTLER_WEB_PASSWORD` and put HTTPS in front of it.
- **Telegram is locked by default.** The bot answers nobody until you add your user ID to `TELEGRAM_ALLOWED_USER_IDS`.
- **Risky actions need approval.** Orders, bookings, calendar changes, address changes and clearing a cart always ask first.

## Project status and limitations

- **Agent memory is in-process:** web chats are saved (sidebar and transcripts survive restarts), but after a restart Butler doesn't remember the earlier context of a chat. Telegram and terminal chats aren't saved.
- **Gmail is read-only:** no sending or deleting. **Calendar** covers your primary calendar only.
- **Swiggy:** India only. Food, Instamart and Dineout are supported (not Scenes yet). Logins last 5 days, and Dineout paid deals and cancellations need the Swiggy app.
- **Model choice:** works with `gpt-4o-mini`, but with all Swiggy services (49 tools) **`gpt-4.1-mini` is recommended**. It's much more reliable at carts and bookings. Set `OPENAI_MODEL`, or trim with `SWIGGY_SERVICES`.

## Contributing

Issues and pull requests are welcome. See [Architecture](docs/architecture.md) for how the code is organised, and [Adding tools](docs/internals/adding-tools.md) for step-by-step recipes for new tools and integrations.

## License

[MIT](LICENSE) © 2026 Butler contributors
