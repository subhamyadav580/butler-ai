# Adding tools

Step-by-step recipes, from the smallest change to the largest. Read [Tools](tools.md) first for how tools work.

| I want to… | Recipe |
|---|---|
| Add one more Gmail action | [1. Add a tool to an existing integration](#1-add-a-tool-to-an-existing-integration) |
| Connect a new service through its Python SDK or REST API | [2. Add a new integration](#2-add-a-new-integration) |
| Add another Swiggy service (Scenes, …) | [3. Add another Swiggy MCP server](#3-add-another-swiggy-mcp-server) |
| Connect any other MCP server | [4. Add a third-party MCP server](#4-add-a-third-party-mcp-server) |
| Make a tool ask before acting | [5. Require approval for a tool](#5-require-approval-for-a-tool) |
| Ask the user a new kind of question | [6. Add a new kind of question](#6-add-a-new-kind-of-question) |

At the end: [Checklist](#checklist) and [Testing](#testing).

## 1. Add a tool to an existing integration

Example: let Butler list your Gmail labels.

**Add the logic** to the client ([gmail/client.py](../../butler/integrations/gmail/client.py)):

```python
def list_labels(self):
    result = self.service.users().labels().list(userId="me").execute()
    return [label["name"] for label in result.get("labels", [])]
```

**Expose it as a tool** ([gmail/tools.py](../../butler/integrations/gmail/tools.py)):

```python
@tool
def list_labels() -> list[str]:
    """List the names of the user's Gmail labels (system and custom).

    Use when the user asks which labels or folders they have.
    """
    return _client().list_labels()


GMAIL_TOOLS = [get_emails, pick_email, read_email, count_unread, inbox_overview, list_labels]
```

That's all: `GMAIL_TOOLS` is already registered with the agent. Restart Butler and ask "what labels do I have?".

Optionally, if the tool needs workflow guidance the description can't give, add a line to `GMAIL_RULES` in [agent/prompts.py](../../butler/agent/prompts.py).

## 2. Add a new integration

Example: **Google Calendar**. This is now implemented, so use [`butler/integrations/calendar/`](../../butler/integrations/calendar/) as the reference while reading. The steps below are how it was built and apply to any new Python integration, such as Google Tasks or Notion.

### 2.1 Files

```
butler/integrations/calendar/
├── __init__.py      exports CALENDAR_TOOLS
├── config.py        scopes, token path, login command
├── auth.py          credentials; never opens a browser unless interactive=True
├── client.py        a small class wrapping the API
├── tools.py         @tool functions + CALENDAR_TOOLS
└── login.py         `python -m butler calendar-login`
```

### 2.2 Config and token path

Add the token path in [butler/config.py](../../butler/config.py), next to the others:

```python
CALENDAR_TOKEN_FILE = SECRETS_DIR / "calendar_token.json"
```

`calendar/config.py`:

```python
from butler.config import CALENDAR_TOKEN_FILE, GOOGLE_CLIENT_SECRET_FILE

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = str(GOOGLE_CLIENT_SECRET_FILE)   # same Google OAuth client as Gmail
TOKEN_FILE = str(CALENDAR_TOKEN_FILE)
LOGIN_COMMAND = "python -m butler calendar-login"
```

### 2.3 Auth: the one rule that matters

For Google services, call the shared [google_oauth.get_credentials()](../../butler/integrations/google_oauth.py) (Gmail and Calendar both do). For other services, keep the same key behaviour:

```python
def get_calendar_service(interactive=False):
    ...
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif not interactive:
            # The agent must never open a browser: the chat would hang
            raise CalendarLoginRequired(f"Calendar is not connected. Run `{LOGIN_COMMAND}`.")
        else:
            creds = InstalledAppFlow.from_client_secrets_file(...).run_local_server(port=0)
```

Tools use `interactive=False`; only `login.py` and the web UI's Connect button use `interactive=True`.

### 2.4 Tools

```python
@tool
def upcoming_events(days: int = 7, limit: int = 10) -> list[dict]:
    """List the user's calendar events in the next `days` days.

    Args:
        days: How far ahead to look (1-60).
        limit: Maximum events to return (1-50).
    """
    events = _client().upcoming(max(1, min(days, 60)), max(1, min(limit, 50)))
    return [{"id": e["id"], "title": e.get("summary", ""), "start": e["start"],
             "end": e["end"], "location": e.get("location")} for e in events]


CALENDAR_TOOLS = [upcoming_events]
```

Return compact dicts: whatever you return is re-sent to the LLM on every later turn.

### 2.5 Register with the agent

[agent/graph.py](../../butler/agent/graph.py):

```python
from butler.integrations.calendar import CALENDAR_TOOLS

all_tools = GMAIL_TOOLS + CALENDAR_TOOLS + swiggy_tools
...
llm_without_swiggy = llm.bind_tools(GMAIL_TOOLS + CALENDAR_TOOLS)
```

[agent/prompts.py](../../butler/agent/prompts.py): add a `CALENDAR_RULES` block (time zone, date format, when to use the tool) and include it in `system_prompt()`.

### 2.6 Login command

[butler/__main__.py](../../butler/__main__.py): add `"calendar-login"` to `COMMANDS` and a branch:

```python
elif command == "calendar-login":
    from butler.integrations.calendar import login as calendar_login
    calendar_login.main()
```

### 2.7 Show it in the web UI

[web/services/integration_service.py](../../butler/web/services/integration_service.py):

1. Add a `_calendar_status()` that returns `{name, title, description, state, detail, ...}`, where `state` is `connected`, `disconnected` or `needs_setup`, and append it in `list_status()`.
2. Add `"calendar": self._connect_calendar` to the `flows` dict in `connect()`, running your login with `interactive=True` inside `asyncio.to_thread(...)`.

The Integrations page renders it automatically; no frontend change is needed.

### 2.8 Document it

Add `docs/integrations/calendar.md` (setup and what you can ask), link it from the README's integration table, and add any new `.env` settings to [configuration.md](../configuration.md) and `.env.example`.

## 3. Add another Swiggy MCP server

Food, Instamart and Dineout are already integrated. Swiggy also runs **Scenes** (events and tickets, `https://mcp.swiggy.com/scenes`). Adding it, or any future Swiggy service, works like this:

1. **Add the URL** to `ALL_SERVERS` in [swiggy/config.py](../../butler/integrations/swiggy/config.py), and add the name to the default `SWIGGY_SERVICES` in [butler/config.py](../../butler/config.py):

   ```python
   ALL_SERVERS = {
       ...,
       "scenes": "https://mcp.swiggy.com/scenes",
   }
   ```

   Its tools load automatically as `scenes_<tool>`. Don't rely on Swiggy's docs saying names are unique: Food, Instamart and Dineout share several names, which is why every tool is prefixed.

2. **List the real tools.** Run `python -m butler swiggy-login`, which prints every tool per service. The existing login covers all servers, because the token is issued for `https://mcp.swiggy.com/`. Swiggy's documentation doesn't always match what the server returns: Instamart's docs list 19 tools, but the server returns 16. Trust the output.

3. **Drop useless tools.** Add support-only or widget-only tools to `EXCLUDED_TOOLS`.

4. **Gate risky tools.** Add every tool that orders, pays, books, cancels, or changes addresses to `NEEDS_APPROVAL`, with the question for the card. If a cart or summary tool exists, add a preview in `_preview()`.

5. **Teach the workflow.** Add a `SCENES_RULES` block in [agent/prompts.py](../../butler/agent/prompts.py), register it in `SERVICE_RULES` and in the order in `system_prompt()`. Read the tools' own descriptions first; they often contain required steps such as "call X before Y" or "this replaces the whole cart".

6. **Add the labels.** In the web UI, add status labels for the new tools in `TOOL_LABELS` ([Chat.tsx](../../frontend/src/components/Chat.tsx)).

7. **Test** with approvals **rejected**, and leave any test cart empty afterwards. See [Testing](#testing).

8. **Watch the tool count.** Today there are 49 tools (5 Gmail and 44 Swiggy). Each service adds 10–20. Smaller models choose worse as the list grows; recommend `gpt-4.1-mini` or better, or let users trim with `SWIGGY_SERVICES`.

## 4. Add a third-party MCP server

Any MCP server works the same way: discover its tools, wrap them, register them.

```python
# integrations/<name>/client.py
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_<name>_tools():
    client = MultiServerMCPClient({
        "<name>": {
            "transport": "streamable_http",                  # or "stdio" for a local process
            "url": "https://example.com/mcp",
            "headers": {"Authorization": f"Bearer {API_KEY}"},   # API-key servers
            # "auth": OAuthClientProvider(...),              # OAuth servers (see swiggy/auth.py)
        }
    })
    return await client.get_tools()
```

A local server started as a subprocess uses `{"transport": "stdio", "command": "npx", "args": ["-y", "@some/mcp-server"]}`.

Then:

1. **Wrap the tools.** Reuse the ideas in `swiggy/tools.py`:
   - `_openai_compatible()`: needed if the server's schemas use top-level `anyOf`/`oneOf`
   - `_to_text()`: flatten MCP content blocks
   - an approval set for risky tools
   - turn auth errors into a clear "run `<name>-login`" message
2. **Load it in `build_graph()`** like Swiggy: `tools, error = await load_<name>_tools()`. Return `[]` when it isn't connected, so Butler still starts.
3. **Add prompt rules, a login command if it uses OAuth, an Integrations entry and docs**, as in recipe 2.

## 5. Require approval for a tool

**MCP tools:** add the tool's (prefixed) name to `NEEDS_APPROVAL` in the integration's `tools.py`, with the question to show. Optionally add a preview in `_preview()`.

**Your own Python tools:** call `interrupt()` before doing anything irreversible:

```python
from langgraph.types import interrupt

@tool
def delete_event(event_id: str) -> str:
    """Delete a calendar event. Asks the user to approve first."""
    event = _client().get_event(event_id)          # read-only: safe to repeat

    answer = interrupt({
        "type": "confirm_action",                  # every interface already renders this
        "question": "Delete this calendar event?",
        "tool": "delete_event",
        "args": {"event_id": event_id},
        "details": f"{event['summary']} — {event['start']}",
    })
    if not (answer or {}).get("approved"):
        return "The user rejected deleting the event. Nothing was changed."

    _client().delete_event(event_id)               # only after approval
    return "Event deleted."
```

> **Important:** on resume, the tool **runs again from the top**, and `interrupt()` then returns the answer instead of pausing. Everything *before* `interrupt()` must be safe to run twice (reads only). Do the irreversible work only *after* it.

## 6. Add a new kind of question

`pick_email` and `confirm_action` already exist. For something new, say choosing a time slot (`pick_slot`):

1. **Raise it** in your tool: `answer = interrupt({"type": "pick_slot", "question": ..., "slots": [...]})`.
2. **Cancel value:** add `"pick_slot": {"slot_id": None}` to `CANCEL_ANSWERS` in [agent/human.py](../../butler/agent/human.py). It's used when the user sends a new message instead of answering.
3. **Terminal:** add a `ask_user_to_pick_slot()` and register it in `HUMAN_PROMPTS` in [interfaces/cli.py](../../butler/interfaces/cli.py).
4. **Telegram:** add a renderer to `HUMAN_PROMPTS`, a callback prefix plus a `CallbackQueryHandler`, and typed-answer handling in `typed_answer()`, all in [interfaces/telegram_bot.py](../../butler/interfaces/telegram_bot.py).
5. **Web:**
   - backend: add `"pick_slot"` to `ResumeRequest.type` and a `PickSlotAnswer` schema in `ANSWER_SCHEMAS` ([web/handlers/chat.py](../../butler/web/handlers/chat.py))
   - frontend: add the payload type in `types.ts`, a component in `frontend/src/components/`, and render it in `Chat.tsx`

See [Human in the loop](human-in-the-loop.md) for how it fits together.

## Checklist

- [ ] The tool's **description** says what it does and when to use it, written for the LLM
- [ ] Arguments are **typed**, have **defaults**, and numbers are **clamped**
- [ ] Results are **compact**: IDs plus the fields the LLM needs; long text truncated
- [ ] Tools **never open a browser** or block; login only via `interactive=True` paths
- [ ] **Irreversible actions require approval**, with no side effects before `interrupt()`
- [ ] Not-connected and auth errors produce a **clear sentence**, and Butler still **starts** without the integration
- [ ] **Prompt rules** cover workflow ordering and quirks of the outside service
- [ ] **Secrets** go in `secrets/` (git-ignored); new settings go in `config.py` and `.env.example`
- [ ] **Docs** updated: an integration guide, the README table, configuration

## Testing

1. **The tool alone**, no LLM:

   ```bash
   python -c "from butler.integrations.gmail.tools import list_labels; print(list_labels.invoke({}))"
   ```

2. **Through the agent**, in the terminal: `python -m butler chat`, then ask naturally *and* in odd phrasings. Check the tool is picked and nothing else is called by mistake.

3. **The not-connected path:** move the token file away and confirm Butler starts, and that asking gives a clear "not connected" answer instead of an error or a hang.

4. **Approvals:** for gated tools, test **Reject** first. Confirm nothing changed in the real service before you ever test Approve.

5. **All interfaces**, if you added a new kind of question: terminal, Telegram and web.
