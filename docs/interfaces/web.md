# Web UI

A chat app in your browser, with live (streamed) replies, a conversation list, an email picker, Approve/Reject buttons, and an **Integrations** page for connecting your accounts. It works on desktop and phone, in light and dark mode.

## Start it

Build the frontend once (needs Node 20+):

```bash
cd frontend
npm install
npm run build
cd ..
```

Then start the server:

```bash
python -m butler web
```

Open **http://127.0.0.1:8000**.

Rebuild the frontend (`npm run build`) after you pull updates that change `frontend/`.

## Using it

- **Chat:** type a message and press **Enter** (**Shift+Enter** for a new line). Replies appear as they're written, with a status line while Butler works ("Searching your mail…").
- **Conversations:** **+ New chat** starts a fresh conversation. Earlier ones are listed in the sidebar. **Double-click** a title to rename it; the **×** deletes it.
- **Email picker:** when you ask to open an email, Butler shows a list. Click one to read it, or **Cancel**.
- **Approvals:** before Butler places an order, changes an address or clears your cart, it shows a card with the details and **Approve / Reject**.
- **Todos:** your todo list, grouped by list. Add, tick off, filter and delete. See [Todos](../integrations/todos.md).
- **Integrations:** shows whether Gmail, Calendar and Swiggy are connected, how long the Swiggy login has left, which Swiggy services are loaded, and a **Connect** or **Reconnect** button. Cards can have switches, such as Gmail's **Allow replying & sending**; the **Web search** card has an on/off switch per provider and **Use first**.

## Where chats are stored

| What | Where | After a restart |
|---|---|---|
| The sidebar list and every chat's messages | SQLite at `data/butler.db` | ✅ Still there, on every device and browser |
| Todos | The same database | ✅ Kept, and shared with Telegram and the terminal |
| Butler's working memory (tool results, an open picker or approval) | RAM | ❌ Starts fresh |

So after restarting Butler you can open and read any old chat, but Butler doesn't remember its earlier context; it continues from your next message. A new chat is only saved once you send its first message, so empty chats never pile up.

To back up your chat history, copy `data/butler.db`. To wipe it, stop Butler and delete the file.

## Connecting accounts from the browser

Clicking **Connect** or **Reconnect** always opens a fresh login, the same one the CLI commands run. If you cancel it, your previous login keeps working. The login window opens in a browser **on the machine running Butler**. That's normal for a self-hosted app: the person running the server is the person whose accounts get connected.

If Butler runs on a remote server with no browser, connect on your laptop instead (`gmail-login`, `calendar-login`, `swiggy-login`) and copy the `secrets/` folder to the server.

## Protecting it

By default the server only listens on `127.0.0.1`, so only your own computer can open it. To open it from other devices, such as your phone on the same Wi-Fi:

```
BUTLER_WEB_HOST=0.0.0.0
BUTLER_WEB_PASSWORD=choose-a-long-password
```

With a password set, the UI shows a login screen, and every API call needs the token you get from logging in.

> ⚠️ Without a password, anyone who can reach the address can read your mail and order on your Swiggy account. Butler prints a warning if you expose it without one. If you put it on the internet, also put HTTPS in front of it (Caddy, nginx, or a tunnel such as Cloudflare Tunnel or Tailscale).

## Developing the frontend

Run the API server and the Vite dev server side by side:

```bash
python -m butler web          # terminal 1: API on :8000
cd frontend && npm run dev    # terminal 2: UI on :5173 with hot reload
```

Open **http://localhost:5173**. Vite forwards `/api` calls to port 8000 (see `frontend/vite.config.ts`).

## API

The UI is a thin client over a small JSON API. FastAPI serves interactive docs at **http://127.0.0.1:8000/docs**.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/chat/messages` | Send a message; the reply streams back as Server-Sent Events |
| `POST` | `/api/chat/resume` | Answer a picker or approval; also streams |
| `GET` | `/api/chat/threads` | The sidebar list (newest first) |
| `GET` | `/api/chat/threads/{id}` | Saved messages, plus any open question |
| `PATCH` | `/api/chat/threads/{id}` | Rename: `{"title": "..."}` |
| `DELETE` | `/api/chat/threads/{id}` | Delete a conversation and its messages |
| `GET` | `/api/todos?status=open\|done\|all` | Todos, open first and by due date |
| `POST` | `/api/todos` | Add: `{"title", "due"?, "list"?, "priority"?, "notes"?}` |
| `PATCH` | `/api/todos/{id}` | Change fields, or `{"done": true}` |
| `DELETE` | `/api/todos/{id}` | Delete a todo |
| `GET` | `/api/todos/lists` | Lists with open and done counts |
| `GET` | `/api/integrations` | Connection status |
| `POST` | `/api/integrations/{name}/connect` | Start a login (`gmail`, `calendar`, `swiggy`) |
| `POST` | `/api/integrations/reload` | Reload the agent's tools |
| `PUT` | `/api/integrations/{name}/options/{key}` | Flip an integration's switch, e.g. Gmail's `send_enabled`: `{"value": true}` |
| `GET` / `PUT` | `/api/integrations/web-search` | Web search providers: list them, switch them on or off, choose which is used first |
| `GET` | `/api/auth/status`, `POST /api/auth/login` | Password login |

Stream events look like `data: {"type": "token" | "tool" | "interrupt" | "done" | "error", ...}`.
