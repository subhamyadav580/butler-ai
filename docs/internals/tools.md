# Tools

Everything Butler can *do* beyond talking is a **tool**: a function the LLM can call, with a name, a description, and typed arguments. To the agent, every tool looks the same: a LangChain `BaseTool` in the `all_tools` list. Behind that, Butler has two kinds.

| | Python tools (Gmail) | MCP tools (Swiggy) |
|---|---|---|
| Defined | In our code, with `@tool` | By the remote service, discovered at startup |
| Runs | Our Python calling Google's API | A JSON-RPC call to `mcp.swiggy.com` |
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

[MCP](https://modelcontextprotocol.io) (Model Context Protocol) lets a service publish tools that any agent can discover and call. Swiggy runs an MCP server; Butler is the client.

### Discovery

```python
# integrations/swiggy/client.py
MultiServerMCPClient({
    "swiggy_food": {
        "transport": "streamable_http",
        "url": "https://mcp.swiggy.com/food",
        "auth": make_auth(),          # OAuth (see Auth and security)
    }
}).get_tools()
```

`langchain-mcp-adapters` asks the server which tools it has (`tools/list`) and turns each into a LangChain tool, with the server's name, description and JSON schema. Swiggy Food returns 20 tools. Butler doesn't hard-code them, so new Swiggy tools appear automatically.

### Wrapping

Raw MCP tools go to the agent only after `_wrap()` in [swiggy/tools.py](../../butler/integrations/swiggy/tools.py). Each wrapper does this:

```
LLM calls update_food_cart(args)
  │
  ├─ 1. Access check   swiggy_allowed false (from the run's config)? → "not available for this user"
  ├─ 2. Approval       name in NEEDS_APPROVAL? → interrupt(confirm_action) → rejected? stop
  ├─ 3. Call           the real MCP tool
  ├─ 4. Login errors   SwiggyLoginRequired → "login expired, run swiggy-login"
  └─ 5. Clean up       MCP content blocks → plain text; drop "widget" instructions
```

**Approvals** are a fixed list of tools that change something real:

```python
NEEDS_APPROVAL = {"place_food_order", "confirm_order", "create_address",
                  "delete_address", "flush_food_cart"}
```

The order tools also fetch the current cart, so the approval card shows what's being ordered. See [Human in the loop](human-in-the-loop.md).

**Result cleanup.** Swiggy's results are written for clients that draw a cart "widget", and they tell the LLM *"do not repeat the cart items, prices, or totals"*. Butler has no widget, so `_strip_widget_notes()` removes those lines; otherwise the LLM would hide the cart from you.

### Schema fixes for OpenAI

OpenAI rejects a tool schema that has `anyOf`, `oneOf` or `allOf` at the **top level**. Swiggy uses that pattern for "pass `addressId` **or** `latitude` + `longitude`". `_openai_compatible()` removes the combinator and appends the rule to the description:

```
…tool description…

You must provide: addressId OR latitude + longitude.
```

Swiggy's server still validates the real rule.

### Undocumented requirements

Some quirks can't be fixed in the schema, so they go in the prompt's `SWIGGY_RULES`, for example: "`update_food_cart` needs `addressId` even though the schema doesn't list it". When an MCP tool keeps failing the same way, check the error text and add a rule.

## How tools are registered

[agent/graph.py](../../butler/agent/graph.py):

```python
swiggy_tools, swiggy_error = await load_swiggy_tools()   # [] if not connected
all_tools = GMAIL_TOOLS + swiggy_tools

llm.bind_tools(all_tools)                                 # the LLM sees the schemas
ToolNode(all_tools, handle_tool_errors=True)              # the graph can run them
```

A tool must be in **both**: bound to the LLM so it can be *called*, and in the `ToolNode` so it can be *run*.

## Good tool design

- **One clear job per tool.** `get_emails` (list) and `read_email` (one full email) beat one tool with a `mode` argument.
- **Few, typed arguments with defaults.** Use `Literal` for fixed choices, `Optional[...] = None` for filters, and clamp numbers (`max(1, min(limit, 50))`).
- **Return less.** Only what the LLM needs to answer or chain to the next call: IDs, names, short text.
- **Fail with a sentence.** A clear exception message ("Gmail is not connected. Run …") becomes a useful reply to the user, thanks to `handle_tool_errors`.
- **Never block on a human inside a tool**, except through `interrupt()`.
- **Gate anything irreversible** behind an approval.

Ready to add one? See [Adding tools](adding-tools.md).
