# Todos

Butler keeps its own todo list. You can manage it by chatting (web UI, Telegram, terminal) or on the web UI's **Todos** page. Nothing to set up or connect: todos are stored in Butler's local database (`data/butler.db`), so they work as soon as Butler runs.

## What you can ask

```
Remind me to pay rent on Friday, it's important
Add buy eggs and milk to my groceries list
What's on my list?
What do I need to do today?
What's left on my Work list?
I paid the rent                       ← marks it done
Move the report one to Monday
Make "call the bank" high priority
Delete the eggs one                   ← asks you to Approve
```

| Tool | Does | Asks first? |
|---|---|---|
| `add_todo` | New todo with an optional due date or time, list, priority and notes | No |
| `list_todos` | Open, done or all; filter by list, text, or "due by" a date | No |
| `complete_todo` | Mark done, or reopen | No |
| `update_todo` | Change title, due date (or clear it), list, priority, notes | No |
| `delete_todo` | Remove permanently | ✅ |
| `todo_lists` | Your lists with open and done counts | No |

## What a todo has

| Field | Notes |
|---|---|
| **Title** | Required. Short: "Pay electricity bill" |
| **Due** | Optional. A date (`2026-10-16`, due by the end of that day) or a date and time (`2026-10-16T18:00`). Past-due open todos are marked **overdue** and listed first |
| **List** | Optional, default **Inbox**. Lists are created when first used, and matched without regard to case: "work" goes to your existing "Work" list |
| **Priority** | `low`, `normal` (default) or `high` |
| **Notes** | Optional details |
| **ID** | A short number like `#12`, shown everywhere, so you can say "mark #12 done" |

Open todos are sorted **overdue → soonest due → no due date**, and by priority within the same due time.

## The Todos page (web UI)

Open **☑ Todos** in the sidebar:

- **Add:** type a title, optionally pick a due date, a list (existing lists are suggested) and a priority, then press **Enter** or **Add**.
- **Complete:** tick the checkbox.
- **Filter:** **Open**, **Done** or **All**.
- **Delete:** hover a todo and click **×**. This doesn't ask first; asking only applies when Butler deletes on your behalf in chat.
- **Grouped by list.** Overdue dates show in red, high priority with a red **!**.

The page refreshes when you come back to the tab, so todos Butler added from a chat or Telegram show up.

## Reminders

Butler **doesn't send notifications** yet. When you say "remind me…", it saves a todo with that due time and can also add the reminder to your **Google Calendar**, whose notifications will alert you (if Calendar is connected).

## Good to know

- **Shared by every interface.** The web UI, Telegram and the terminal all read and write the same list in `data/butler.db`, even when running at the same time.
- **One list per Butler instance.** Everyone allowed to use your Butler (for example on Telegram) sees the same todos.
- **Backing up or moving:** copy `data/butler.db`. It also holds your saved web chats.
- **Not Google Tasks.** These todos are Butler's own, so they don't appear in the Google Tasks app.
- **API:** `GET/POST /api/todos`, `PATCH/DELETE /api/todos/{id}`, `GET /api/todos/lists`. See [Web UI → API](../interfaces/web.md#api).
- **Where the code lives:** [`butler/integrations/todos/`](../../butler/integrations/todos/): `repo.py` (table and queries), `service.py` (rules, shared with the web API) and `tools.py` (the agent's tools).
