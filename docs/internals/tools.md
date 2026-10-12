# Tools

Everything Butler can *do* beyond talking is a **tool**: a function the LLM can call, with a name, a description, and typed arguments. To the agent, every tool looks the same: a LangChain `BaseTool` in the `all_tools` list. Behind that, Butler has two kinds.

| | Python tools (Gmail, Calendar, Todos, Web search) | MCP tools (Swiggy) |
|---|---|---|
| Defined | In our code, with `@tool` | By the remote service, discovered at startup |
| Runs | Our Python calling Google's APIs, a search provider's API, or Butler's own database (todos) | A JSON-RPC call to `mcp.swiggy.com/{food,im,dineout}` |
| Sync/async | Sync, run in a thread by `ToolNode` | Async |
| Wrapped by us | Not needed | Yes: access check, approvals, result cleanup, schema fix |
| Code | [integrations/gmail/tools.py](../../butler/integrations/gmail/tools.py) | [integrations/swiggy/tools.py](../../butler/integrations/swiggy/tools.py) |

## What the LLM sees

For each tool, the LLM receives a JSON schema built from the tool's name, docstring and argument types:

```json
{
  "name": "count_unread",
  "description": "Exact number of unread emails in a Gmail tab or folder.",
  "parameters": {
    "type": "object",
    "properties": {"category": {"enum": ["primary", "promotions", "…"], "default": "primary"}}
  }
}
```

The description is the **only** documentation the LLM has, so it decides when the tool gets used. Write it as instructions to the model: what the tool is for, when to use it instead of a similar tool, and what each argument means.

## Python tools: Gmail

```python
from langchain_core.tools import tool

@tool
def count_unread(category: Category = "primary") -> int:
    """Exact number of unread emails in a Gmail tab or folder."""
    return _client().unread_count(category)

GMAIL_TOOLS = [get_emails, pick_email, read_email, count_unread, inbox_overview]
```

- **Arguments:** type hints become the schema. `Literal[...]` (the `Category` type) becomes an `enum`, so the LLM can only pick valid values.
- **Docstrings:** the `Args:` section becomes per-argument descriptions.
- **Return values:** returned values are serialised into the `ToolMessage` the LLM reads. Return **compact, relevant data**. `_compact()` strips Gmail's raw message down to id, from, to, subject, date, snippet and unread, and email bodies are cut to 4,000 characters (`MAX_BODY_CHARS`), because every result is re-sent on later turns (see [Memory](memory.md)).
- **Shared client:** one `Gmail` client is reused, and it keeps one Google API connection **per thread**, because `ToolNode` runs parallel calls in threads and `httplib2` isn't thread-safe.
- **No logins inside tools:** the agent's Gmail client is created with `interactive=False`. If Gmail isn't connected, the tool raises `GmailLoginRequired` with instructions, instead of opening a browser and hanging the chat.

The layers underneath, so tools stay thin:

```
tools.py      @tool functions: arguments in, compact dicts out
client.py     Gmail class: get_emails, get_email, unread_count, …
query.py      category + filters → Gmail search string ("in:inbox category:updates from:(linkedin) is:unread")
parser.py     raw Gmail message → dict; decode body; unescape snippet
auth.py       OAuth credentials, token file, interactive or not
```

## MCP tools: Swiggy

[MCP](https://modelcontextprotocol.io) (Model Context Protocol) lets a service publish tools that any agent can discover and call. Swiggy runs one MCP server per service; Butler is the client.

| Service | Server | Tools used |
|---|---|---|
| Food | `https://mcp.swiggy.com/food` | 19 |
| Instamart | `https://mcp.swiggy.com/im` | 15 |
| Dineout | `https://mcp.swiggy.com/dineout` | 10 |

Choose which to load with `SWIGGY_SERVICES` (default: all three); see [swiggy/config.py](../../butler/integrations/swiggy/config.py).

### Discovery

```python
# integrations/swiggy/client.py: one client per server
MultiServerMCPClient(
    {"instamart": {"transport": "streamable_http",
                   "url": "https://mcp.swiggy.com/im",
                   "auth": make_auth()}},          # OAuth (see Auth and security)
    tool_name_prefix=True,
).get_tools()
```

`langchain-mcp-adapters` asks each server which tools it has (`tools/list`) and turns each into a LangChain tool, with the server's name, description and JSON schema. Butler doesn't hard-code them, so new Swiggy tools appear automatically.

### Name prefixes

Several tool names exist on more than one server: `get_addresses`, `create_address`, `delete_address`, `get_payment_options`, `check_payment_status`, `confirm_order` and `report_error`. OpenAI rejects duplicate tool names, so every tool gets its service as a prefix:

```
food_get_addresses        instamart_get_addresses      dineout_get_saved_locations
food_update_food_cart     instamart_update_cart        dineout_book_table
food_confirm_order        instamart_confirm_order      dineout_confirm_order
```

The prefix also tells the model which service a tool belongs to. The adapter maps a prefixed name back to the original when it calls the server.

### Excluded tools

`EXCLUDED_TOOLS` in `swiggy/config.py` keeps four tools away from the LLM:

- the three `*_report_error` tools, which file bug reports with Swiggy's MCP team
- `dineout_render_restaurants_dineout`, which only draws a widget Butler doesn't have

### Loading each server independently

`get_swiggy_tools()` loads one server at a time:

- **Rate limited (`429`):** retry after 2 seconds, then after 5.
- **Still failing:** skip that server and record why. The other services keep working, the startup warning names the missing one, and the web UI's Integrations page shows it.
- **Login problem:** stop immediately, because it affects every server.

### Wrapping

Raw MCP tools go to the agent only after `_wrap()` in [swiggy/tools.py](../../butler/integrations/swiggy/tools.py). Each wrapper does this:

```
LLM calls instamart_checkout(args)
  │
  ├─ 1. Access check   allow_restricted false (from the run's config)? → "not available for this user"
  ├─ 2. Approval       name in NEEDS_APPROVAL? → build preview → interrupt(confirm_action) → rejected? stop
  ├─ 3. Call           the real MCP tool
  ├─ 4. Login errors   → "login expired, run swiggy-login"
  └─ 5. Clean up       MCP content blocks → plain text; drop "widget" instructions
```

**Approvals.** `NEEDS_APPROVAL` maps each tool that changes something real to the question shown on the card:

```python
NEEDS_APPROVAL = {
    "food_place_food_order": "Place this Swiggy Food order?",
    "instamart_checkout": "Place this Instamart order?",
    "dineout_book_table": "Book this table on Swiggy Dineout?",
    # … confirm_order, create/delete_address and cart clearing for each service
}
```

**Previews.** `_preview()` adds context to the card using read-only calls, which are safe to repeat on resume:

| Approval for | Preview |
|---|---|
| Food orders | The Food cart (`food_get_food_cart`) |
| Instamart orders | The Instamart cart (`instamart_get_cart`) |
| Dineout bookings | Guests, time and payment from the arguments, plus restaurant details |

See [Human in the loop](human-in-the-loop.md).

**Result cleanup.** Swiggy's results are written for clients that draw a cart "widget", and they tell the LLM *"do not repeat the cart items, prices, or totals"*. Butler has no widget, so `_strip_widget_notes()` removes those lines; otherwise the LLM would hide the cart from you.

### Schema fixes for OpenAI

OpenAI rejects a tool schema that has `anyOf`, `oneOf` or `allOf` at the **top level**. Swiggy Food uses that pattern for "pass `addressId` **or** `latitude` + `longitude`". `_openai_compatible()` removes the combinator and appends the rule to the description:

```
…tool description…

You must provide: addressId OR latitude + longitude.
```

Swiggy's server still validates the real rule.

### Rules the schema can't express

Workflow knowledge goes in the prompt, in [swiggy/integration.py](../../butler/integrations/swiggy/integration.py): one shared `COMMON_RULES` block, plus `FOOD_RULES`, `INSTAMART_RULES` and `DINEOUT_RULES`, each included only when that service loaded. Examples:

- `food_update_food_cart` needs `addressId` even though the schema doesn't list it.
- `instamart_update_cart` **replaces the whole cart**, so always re-send the items already in it.
- Dineout paid deals need UPI in the Swiggy app, so prefer free slots.
- There's no widget: ignore tool text about tapping buttons, and write results out in full.

The prompt also overrides Swiggy's own tool descriptions where they clash with a chat UI. For example, they say to always re-confirm the address, while Butler uses the address you named. When a tool keeps failing the same way, check the error text and add a rule.

## How tools are registered

Every integration hands its tools to the agent through its `integration.py`; the agent loops over the [registry](../../butler/integrations/registry.py):

```python
# agent/graph.py, simplified
for integration in INTEGRATIONS:
    tools, warning = await integration.load_tools()   # [] if not configured
    ...
llm.bind_tools(all_tools)                             # the LLM sees the schemas
ToolNode(all_tools, handle_tool_errors=True)          # the graph can run them
```

A tool must be in **both**: bound to the LLM so it can be *called*, and in the `ToolNode` so it can be *run*. The loop takes care of that; an integration only returns its list. See [Adding tools](adding-tools.md#2-add-a-new-integration).

## Good tool design

- **One clear job per tool.** `get_emails` (list) and `read_email` (one full email) beat one tool with a `mode` argument.
- **Few, typed arguments with defaults.** Use `Literal` for fixed choices, `Optional[...] = None` for filters, and clamp numbers (`max(1, min(limit, 50))`).
- **Return less.** Only what the LLM needs to answer or chain to the next call: IDs, names, short text.
- **Fail with a sentence.** A clear exception message ("Gmail is not connected. Run …") becomes a useful reply to the user, thanks to `handle_tool_errors`.
- **Never block on a human inside a tool**, except through `interrupt()`.
- **Gate anything irreversible** behind an approval.

Ready to add one? See [Adding tools](adding-tools.md).
