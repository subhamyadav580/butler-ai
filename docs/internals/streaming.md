# Streaming

The web UI shows replies word by word, plus a status line ("Searching your mail…") while tools run. This uses **plain HTTP with a streamed response in Server-Sent Events (SSE) format**, not WebSockets.

Code: [agent/stream.py](../../butler/agent/stream.py) (`stream_events`: shared by the web UI and the terminal), [web/handlers/chat.py](../../butler/web/handlers/chat.py) (`_sse`), and [frontend/src/api.ts](../../frontend/src/api.ts) (`streamEvents`).

## One turn on the wire

```
Browser                                              Server
  │ POST /api/chat/messages {"thread_id", "message"}   │
  │ ──────────────────────────────────────────────────►│
  │ 200 OK, Content-Type: text/event-stream            │
  │ ◄──────────────────────────────────────────────────│
  │ data: {"type":"tool","name":"get_emails"}          │   status: "Searching your mail…"
  │ data: {"type":"token","content":"You"}             │   text appears…
  │ data: {"type":"token","content":" have 12"}        │
  │ data: {"type":"done","content":"You have 12 …"}    │   turn finished
  │ ◄──────────────── stream ends ─────────────────────│
```

Each turn is one request and one streamed response; no connection stays open between turns. Answering a picker or approval is a new request (`POST /api/chat/resume`) that streams the same way.

## Events

| `type` | Fields | Meaning |
|---|---|---|
| `token` | `content` | A piece of the LLM's reply text |
| `tool` | `name` | The LLM decided to call this tool; the UI shows a friendly label |
| `interrupt` | `payload` | The agent paused for a picker or approval; the stream ends here |
| `done` | `content` | The final reply, complete |
| `error` | `message` | Something failed; the UI shows it |

## Server side

`stream_events()` in [agent/stream.py](../../butler/agent/stream.py) runs the graph with **two stream modes at once**:

```python
async for mode, chunk in graph.astream(graph_input, config,
                                       stream_mode=["messages", "updates"]):
```

- **`messages`** yields `(message_chunk, metadata)` for every token the LLM produces. Butler keeps only chunks from the `agent` node (`metadata["langgraph_node"] == "agent"`):
  - text → a `token` event
  - `tool_call_chunks` with a name → a `tool` event
- **`updates`** yields each node's output when it finishes. A chunk with `__interrupt__` becomes an `interrupt` event, and the turn ends.

The node calls `llm.ainvoke()`, not a streaming method. LangGraph's `messages` mode still captures tokens through callbacks, so nodes don't need special streaming code.

`ChatService` sits in between: it passes events through, and saves the reply text to SQLite when it sees `done` or `interrupt` (see [Memory](memory.md)).

The handler formats each event as one SSE frame:

```python
yield f"data: {json.dumps(event)}\n\n"
```

It uses `StreamingResponse(media_type="text/event-stream")` with `Cache-Control: no-cache` and `X-Accel-Buffering: no`, which stops nginx from buffering the stream.

Errors during the stream become an `error` event, because the `200` status has already been sent. Errors *before* the stream starts use normal status codes:

| Status | When |
|---|---|
| `401` | Login required |
| `409` | Resume sent but nothing is waiting |
| `422` | Invalid answer |

## Browser side

The browser's built-in `EventSource` only supports `GET` and can't send an `Authorization` header. Butler needs `POST` with a JSON body (and the password token), so `streamEvents()` reads the stream by hand:

```ts
const reader = response.body.getReader()
// decode chunks → buffer → split on "\n\n" → parse each "data: {...}" line → onEvent(event)
```

`Chat.tsx` reacts to each event:

| Event | UI |
|---|---|
| `token` | Append to the in-progress reply |
| `tool` | Show the status label |
| `interrupt` | Render a picker or approval card |
| `done` | Commit the message, then refresh the sidebar |

## Why not WebSockets?

| | HTTP streaming (used) | WebSocket |
|---|---|---|
| Fits "ask → streamed answer" | ✅ Exactly | More than needed |
| Auth | Normal header on each request | Token in the URL or first message |
| Proxies and tunnels | Plain HTTP, works everywhere | Needs upgrade support |
| Server state between turns | None | One live connection per tab |

WebSockets (or a long-lived SSE channel) would only be worth it for **server-initiated** pushes, such as "your order is out for delivery" with no message from you first.

## The terminal and Telegram

- **The terminal** streams too. It uses the same `stream_events()` and renders the events live with `rich`: Markdown that grows as tokens arrive, plus a spinner with the tool's label.
- **Telegram** doesn't stream: it uses `graph.ainvoke()` and sends the whole reply at once, showing "typing…" while it waits.
