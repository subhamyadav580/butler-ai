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
- **Conversations:** **+ New chat** starts a fresh conversation. Earlier ones are listed in the sidebar; the **×** deletes one.
- **Email picker:** when you ask to open an email, Butler shows a list. Click one to read it, or **Cancel**.
- **Approvals:** before Butler places an order, changes an address or clears your cart, it shows a card with the details and **Approve / Reject**.
- **Integrations:** shows whether Gmail and Swiggy are connected, how long the Swiggy login has left, and a **Connect** or **Reconnect** button.

## Connecting accounts from the browser

Clicking **Connect** runs the same login as the CLI commands. The login window opens in a browser **on the machine running Butler**. That's normal for a self-hosted app: the person running the server is the person whose accounts get connected.

If Butler runs on a remote server with no browser, connect on your laptop instead (`gmail-login`, `swiggy-login`) and copy the `secrets/` folder to the server.

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
| `GET` | `/api/chat/threads/{id}` | Conversation history, plus any open question |
| `DELETE` | `/api/chat/threads/{id}` | Clear a conversation |
| `GET` | `/api/integrations` | Connection status |
| `POST` | `/api/integrations/{name}/connect` | Start a login (`gmail`, `swiggy`) |
| `POST` | `/api/integrations/reload` | Reload the agent's tools |
| `GET` | `/api/auth/status`, `POST /api/auth/login` | Password login |

Stream events look like `data: {"type": "token" | "tool" | "interrupt" | "done" | "error", ...}`.
