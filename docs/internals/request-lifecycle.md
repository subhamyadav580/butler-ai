# Request lifecycle

This page follows one message through every layer, using the web UI because it has the most layers. Telegram and the terminal skip the HTTP and database parts but share everything from the agent down.

The example message: **"Open a mail from LinkedIn"**.

## 1. Browser → server

`Composer` → `Chat.send()` → `api.sendMessage()` ([frontend/src/api.ts](../../frontend/src/api.ts)):

```http
POST /api/chat/messages
Authorization: Bearer <token, only if a password is set>

{"thread_id": "9a15f81c-…", "message": "Open a mail from LinkedIn"}
```

The `thread_id` is a UUID the browser made when you clicked **+ New chat**. It identifies the conversation everywhere: sidebar, database, and agent memory.

## 2. Route → handler

| Layer | File | Does |
|---|---|---|
| Route | `web/routes/chat.py` | Maps `POST /api/chat/messages` to `handlers.chat.send_message`, behind `require_auth` |
| Handler | `web/handlers/chat.py` | Validates the body (`SendMessageRequest`) and wraps the service's events in a `StreamingResponse` (SSE) |

The response starts immediately; the body keeps arriving while the agent works.

## 3. ChatService: save, then run

`web/services/chat_service.py`, `send_message()`:

1. `threads.create(thread_id, title)` creates the sidebar entry if it's new, titled with the message.
2. `messages.add(thread_id, "user", text)` saves your message in SQLite.
3. It calls `AgentService.send_message()` and passes its events through, collecting the reply text to save later (step 7).

## 4. AgentService: run the graph

`web/services/agent_service.py`:

1. `cancel_pending()`: if this thread was waiting on a picker or approval, answer it with "cancel" first.
2. `graph.astream({"messages": [user message]}, config, stream_mode=["messages", "updates"])`
   - `config = {"configurable": {"thread_id": …, "allow_restricted": True}}` (the web UI is the owner)
3. Each LLM token becomes `{"type": "token"}`, each tool name `{"type": "tool"}`, and a pause `{"type": "interrupt"}`.

## 5. The agent loop

[agent/graph.py](../../butler/agent/graph.py):

```
START → agent → tools → agent → … → END
```

1. **Load memory.** The checkpointer loads `thread_id`'s saved messages, and your new message is appended to them.
2. **`agent` node.** It sends the system prompt plus the full message history to the LLM. The LLM replies with a tool call: `pick_email(category="primary", sender="linkedin")`.
3. **`tools` node.** It runs `pick_email`, which fetches matching emails from Gmail and calls `interrupt({...emails})`. The graph **stops** and the checkpoint records "waiting in `tools`".

## 6. Back to the browser

The stream sends:

```
data: {"type": "tool", "name": "pick_email"}          → "Fetching emails…"
data: {"type": "interrupt", "payload": {"type": "pick_email", "emails": [...]}}
```

`Chat` renders `<EmailPicker>`. You click an email, and the browser sends:

```http
POST /api/chat/resume
{"thread_id": "9a15f81c-…", "type": "pick_email", "answer": {"email_id": "1a12…"}}
```

## 7. Resume and finish

1. The handler validates the answer against the right schema (`PickEmailAnswer`). If nothing is waiting, it returns `409`.
2. `graph.astream(Command(resume={"email_id": …}))` restarts `pick_email` from the top; this time `interrupt()` *returns* the answer. The tool reads the full email.
3. The `agent` node sees the tool result and writes the summary, which streams as `token` events, then `done`.
4. `ChatService` saves the reply text as an `assistant` message and bumps the thread's `updated_at`, which moves it to the top of the sidebar.
5. The browser re-fetches the sidebar (`GET /api/chat/threads`).

## Same flow, other interfaces

| Step | Web | Telegram | Terminal |
|---|---|---|---|
| Input | `POST /api/chat/messages` | Telegram update → `handle_message` | `input()` |
| `thread_id` | Browser UUID | `telegram-<chat_id>` | `cli` |
| Run | `stream_events` → SSE (streamed) | `graph.ainvoke` (whole reply) | `stream_events` → live in the terminal |
| Picker / approval | Cards in the chat | Inline buttons | Numbered list, `y/n` |
| Resume | `POST /api/chat/resume` | Button callback → `Command(resume=…)` | `Command(resume=…)` |
| Transcript saved | ✅ SQLite | ❌ | ❌ |

See also [Memory](memory.md), [Human in the loop](human-in-the-loop.md) and [Streaming](streaming.md).
