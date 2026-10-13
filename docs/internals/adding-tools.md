# Adding tools

Step-by-step recipes, from the smallest change to the largest. Read [Tools](tools.md) first for how tools work.

| I want to… | Recipe |
|---|---|
| Add one more Gmail action | [1. Add a tool to an existing integration](#1-add-a-tool-to-an-existing-integration) |
| Connect a new service through its Python SDK or REST API | [2. Add a new integration](#2-add-a-new-integration) |
| Add another Swiggy service (Scenes, …) | [3. Add another Swiggy MCP server](#3-add-another-swiggy-mcp-server) |
| Connect any other MCP server | [4. Add a third-party MCP server](#4-add-a-third-party-mcp-server) |
| Add a web search provider | [Web search: adding a provider](../integrations/web-search.md#adding-a-provider) |
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

Optionally, in [gmail/integration.py](../../butler/integrations/gmail/integration.py):
- add a status label to `tool_labels` (`"list_labels": "Checking your labels"`), shown in the web UI while it runs
- add a line to `RULES` if the tool needs workflow guidance its description can't give

## 2. Add a new integration

An integration is **one folder** plus **one line in the registry**. Everything else (the agent, the prompt, the CLI, the web UI's cards and labels, Telegram) reads the registry, so you don't edit any shared code.

Use an existing integration as your template:

| If your integration… | Copy |
|---|---|
| uses Google's APIs (OAuth) | [`calendar/`](../../butler/integrations/calendar/) |
| needs no login (local data, or an API key in `.env`) | [`todos/`](../../butler/integrations/todos/) or [`websearch/`](../../butler/integrations/websearch/) |
| talks to an MCP server | [`zepto/`](../../butler/integrations/zepto/) (one server, the simplest) or [`swiggy/`](../../butler/integrations/swiggy/) (several) |

### 2.1 The folder

```
butler/integrations/notes/
├── __init__.py
├── config.py         its settings from .env (API keys, token file in SECRETS_DIR)
├── tools.py          the LangChain tools (@tool) + NOTES_TOOLS
├── integration.py    INTEGRATION = NotesIntegration(): ties it all together
├── auth.py, client.py, login.py   only if it needs them
```

Keep settings in the integration's own `config.py`, not in `butler/config.py`:

```python
# butler/integrations/notes/config.py
import os
from butler.config import SECRETS_DIR      # importing butler.config also loads .env

NOTES_API_KEY = os.getenv("NOTES_API_KEY", "").strip()
TOKEN_FILE = str(SECRETS_DIR / "notes_token.json")
```

### 2.2 The tools

Plain LangChain tools; see [Tools](tools.md) for good tool design.

```python
# butler/integrations/notes/tools.py
from langchain_core.tools import tool

@tool
def search_notes(query: str, limit: int = 10) -> list[dict]:
    """Search the user's notes by text. Use for 'find my note about…'."""
    return client().search(query, max(1, min(limit, 50)))

NOTES_TOOLS = [search_notes]
```

### 2.3 `integration.py`: everything Butler needs to know

Subclass [`Integration`](../../butler/integrations/base.py) and override only what you need:

```python
# butler/integrations/notes/integration.py
from butler.integrations.base import Integration
from .config import NOTES_API_KEY
from .tools import NOTES_TOOLS

RULES = (
    "Notes (the user's notes app):\n"
    "- Use search_notes for anything the user wrote down before.\n"
)


class NotesIntegration(Integration):
    name = "notes"                       # id: CLI, API, settings
    title = "Notes"                      # shown in the UI
    description = "Search and read your notes."
    tool_labels = {"search_notes": "Searching your notes"}      # web UI status line
    examples = ["Find my note about the trip budget"]           # web UI + Telegram /start

    async def load_tools(self):
        if not NOTES_API_KEY:            # not set up: leave it out, say why at startup
            return [], "notes is off. Add NOTES_API_KEY to .env"
        return NOTES_TOOLS, None

    def rules(self, tool_names):         # its section of the system prompt
        return RULES

    def status(self, loaded_tool_names): # its card on the Integrations page
        if not NOTES_API_KEY:
            return {"state": "needs_setup", "detail": "Add NOTES_API_KEY to .env."}
        return {"state": "connected", "detail": "Connected."}


INTEGRATION = NotesIntegration()
```

What each part does:

| Part | Used by | Default |
|---|---|---|
| `load_tools()` or `tools()` | the agent; return `[]` to leave the integration out | `tools()` returns `[]` |
| `rules(tool_names)` | the system prompt (only when its tools loaded) | no section |
| `status(loaded_tool_names)` | the Integrations page card | "connected" |
| `tool_labels`, `examples` | the web UI status line, the empty chat and Telegram `/start` | none |
| `restricted = True` | owner-only on Telegram (`TELEGRAM_OWNER_ID`), for costly or risky integrations | `False` |
| `login_command`, `login()` | the CLI: `python -m butler notes-login` | none |
| `can_connect`, `connect()` | the **Connect** button on the Integrations page | no button |
| `reload_on_connect` | rebuild the agent after connecting (tools that load at startup) | `False` |
| `cli_commands` | extra CLI commands, like Gmail's `gmail` reader | none |
| `options()`, `set_option()` | on/off switches on its card (Gmail: **Allow replying & sending**). Store values with `butler.db.get_settings()` so every process sees changes at once; read them inside tools or `rules()` so they apply without a restart | no switches |
| `hides_tools()` | tools of *other* integrations to hide while this one is loaded, because it replaces them. [Groceries](../integrations/groceries.md) hides each app's product search so every grocery search goes through `search_groceries` | none |

**Logins:** never open a browser from a tool. Follow the Gmail pattern: `interactive=False` raises "not connected, run `notes-login`", and only `login()` and `connect()` may open a browser. For Google services, use the shared [google_oauth.py](../../butler/integrations/google_oauth.py) (`get_credentials` and `google_status`).

### 2.4 Register it

One line in [butler/integrations/registry.py](../../butler/integrations/registry.py):

```python
from .notes.integration import INTEGRATION as notes

INTEGRATIONS = [gmail, calendar, todos, web_search, swiggy, zepto, notes]
```

The order is the order of prompt sections and Integrations-page cards. Restart Butler, and the integration is in the agent, the prompt, the CLI, the web UI and Telegram.

### 2.5 Document it

- `docs/integrations/notes.md`: setup and what you can ask
- a row in the README's integration table
- its settings in `.env.example` and [configuration.md](../configuration.md)

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

5. **Teach the workflow.** In [swiggy/integration.py](../../butler/integrations/swiggy/integration.py), add a `SCENES_RULES` block and register it in `SERVICE_RULES` (and in the order inside `rules()`). Read the tools' own descriptions first; they often contain required steps such as "call X before Y" or "this replaces the whole cart".

6. **Add the labels.** Add status labels for the new tools to `tool_labels` in the same file, and an example prompt to `examples`.

7. **Test** with approvals **rejected**, and leave any test cart empty afterwards. See [Testing](#testing).

8. **Watch the tool count.** With everything enabled there are already 60+ tools, about 44 of them Swiggy's. Each Swiggy service adds 10–20. Smaller models choose worse as the list grows; recommend `gpt-4.1-mini` or better, or let users trim with `SWIGGY_SERVICES`.

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
            # "auth": make_auth(...),                        # OAuth servers: see mcp_oauth.py, zepto/auth.py
        }
    })
    return await client.get_tools()
```

A local server started as a subprocess uses `{"transport": "stdio", "command": "npx", "args": ["-y", "@some/mcp-server"]}`.

Then:

1. **Log in, if the server uses OAuth.** [`mcp_oauth.py`](../../butler/integrations/mcp_oauth.py) does the whole flow (client registration, PKCE, browser login, token file, refresh). A service only supplies its settings, as in [`zepto/auth.py`](../../butler/integrations/zepto/auth.py): server URL, token file and a free localhost port.
2. **Wrap the tools.** [`zepto/tools.py`](../../butler/integrations/zepto/tools.py) is the template:
   - `openai_compatible()` from [`mcp_tools.py`](../../butler/integrations/mcp_tools.py): needed if the server's schemas use top-level `anyOf`/`oneOf`
   - `to_text()` from `mcp_tools.py`: flatten MCP content blocks
   - which tools need approval: a fixed dict (Swiggy's `NEEDS_APPROVAL`) or a rule (Zepto's `needs_approval()`)
   - turn auth errors into a clear "run `<name>-login`" message
3. **Make it an integration** (recipe 2): return the wrapped tools from `load_tools()` (async is fine), or `[]` with a reason when it isn't configured, so Butler still starts. Set `restricted = True` if it can spend money or change accounts.
4. **Register it and document it**, as in recipe 2.

## 5. Require approval for a tool

**MCP tools:** for Swiggy, add the tool's (prefixed) name to `NEEDS_APPROVAL` in `swiggy/tools.py`, with the question to show, and optionally a preview in `_preview()`. Zepto decides by rule in `needs_approval()`, so most new tools are covered already.

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
