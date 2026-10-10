# Memory

Butler has **two separate kinds of memory**, kept on purpose in two different places.

| | Agent memory | Saved chats |
|---|---|---|
| **What it is** | The conversation **sent to the LLM** as context on every turn | The transcript **shown in the web UI's** sidebar and chat |
| **Contains** | Your messages, Butler's replies, **tool calls and tool results**, any open picker or approval | Your messages and Butler's replies (text only) |
| **Stored in** | RAM (LangGraph `InMemorySaver`) | SQLite (`data/butler.db`) |
| **Survives a restart** | ❌ | ✅ |
| **Used by** | All interfaces | Web UI only |
| **Code** | [agent/graph.py](../../butler/agent/graph.py) | [web/services/chat_service.py](../../butler/web/services/chat_service.py), [web/repos/](../../butler/web/repos/), [web/db/](../../butler/web/db/) |

## Agent memory: the LLM's context

### How it's stored

The graph is compiled with a checkpointer:

```python
graph.compile(checkpointer=InMemorySaver())
```

After **every step** (your message, each LLM reply, each tool result), LangGraph saves the graph's state under the conversation's `thread_id`. On the next turn it loads that state and appends your new message. The state is one list:

```
thread "9a15f81c-…" → messages:
  HumanMessage   "Open a mail from LinkedIn"
  AIMessage      tool_calls=[pick_email(category="primary", sender="linkedin")]
  ToolMessage    {"status": "selected", "email": {"id": "1a12…", "from": …, "body": …}}
  AIMessage      "Here are the details of the email…"
  HumanMessage   "Who sent it?"
  AIMessage      "LinkedIn Job Alerts, jobalerts-noreply@linkedin.com"
```

### How it's used

Every time the `agent` node runs, it sends the system prompt plus the **entire** list:

```python
await agent_llm.ainvoke(
    [{"role": "system", "content": system_prompt(...)}]   # rebuilt each call, never stored
    + with_tool_results(state["messages"])                # ← agent memory
)
```

That's what makes follow-ups work:

- **"Who sent it?"** works because the earlier tool result, with the sender, is in the context.
- **"Add the first one to my cart"** works because the `search_menu` result, with `restaurantId` and item IDs, is there.
- **"Use my Office address"** works because the `food_get_addresses` result, with the address IDs, is there.

### Thread IDs

| Interface | `thread_id` | One memory per… |
|---|---|---|
| Web UI | A UUID made by the browser | Conversation in the sidebar |
| Telegram | `telegram-<chat_id>` | Telegram chat |
| Terminal | `cli` | Terminal session |

### When it's cleared

- **The process restarts.** It lives in RAM.
- **The web UI reloads the agent** (after connecting Swiggy). A new graph means a new, empty checkpointer.
- **You delete a chat** (web ×) or send **`/reset`** (Telegram), which calls `checkpointer.delete_thread(thread_id)`.

### The cost: it grows

Tool results are stored in full, including email bodies of up to 4,000 characters and long Swiggy menus, and they're re-sent on every turn. A long conversation therefore costs more per message, gets slower, and could eventually exceed the model's context window. Today nothing trims it; start a new chat for a new topic. See [Changing how memory works](#changing-how-memory-works) for fixes.

## Saved chats: what the web UI shows

### How they're stored

Two tables in SQLite ([web/db/sqlite.py](../../butler/web/db/sqlite.py)):

```sql
threads  (id TEXT PRIMARY KEY, title, created_at, updated_at)
messages (id, thread_id → threads.id ON DELETE CASCADE,
          role IN ('user','assistant'), content, created_at)
```

### When they're written

`ChatService` wraps every turn:

1. **On send:** create the thread if it's new (titled with the first message, cut to 60 characters), save the user message, and bump `updated_at`.
2. **While streaming:** collect the reply's text tokens.
3. **On `done`, or when the agent pauses** (`interrupt`): save the collected text as an `assistant` message.
4. **If the stream breaks midway:** still save what was shown (`finally` block).

Tool calls and results are **not** saved here; the transcript matches exactly what you saw.

### When they're read

- **`GET /api/chat/threads`:** the sidebar, newest first.
- **`GET /api/chat/threads/{id}`:** the saved messages, plus any open question, which comes from *agent* memory.

New chats are "drafts" in the browser until their first message, so empty chats never reach the database.

## What happens after a restart

```
Before restart:   sidebar ✅   transcript ✅   agent memory ✅
After restart:    sidebar ✅   transcript ✅   agent memory ❌ (empty for every thread)
```

You can open and read any old chat. If you continue it, the LLM sees only your new message, so it doesn't know what was discussed before. Ask "what's my favourite colour?" about something said before the restart, and it can't know.

Telegram and the terminal have only agent memory, so their conversations are gone after a restart.

## Changing how memory works

### Keep agent memory across restarts

Swap the checkpointer for a persistent one. That's one change in `build_graph()`:

```python
# pip install langgraph-checkpoint-sqlite
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

conn = await aiosqlite.connect("data/agent_memory.db")   # keep open for the app's lifetime
return graph.compile(checkpointer=AsyncSqliteSaver(conn))
```

Full context, tool results included, then survives restarts, and Telegram and the web UI could share it. Expect the file to grow; it stores every step.

### Restore context from the saved transcript

A lighter option: the first time an old web chat is used after a restart, prepend its saved user and assistant messages from SQLite to the graph input. The LLM gets the *text* of the conversation back, but not tool results. So "what did we talk about?" works, while "open the second one" doesn't, because the email IDs aren't in the text.

### Limit how much context is sent

To cap cost on long chats, trim before calling the LLM, in the `agent` node:

```python
from langchain_core.messages import trim_messages

history = trim_messages(state["messages"], max_tokens=20_000, strategy="last",
                        token_counter=llm, start_on="human", include_system=False)
```

Or summarise older turns into one message. Trim **before** `with_tool_results()`, and never cut between an `AIMessage` with tool calls and its `ToolMessage`s; `start_on="human"` takes care of that.
