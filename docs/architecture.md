# Architecture

This page is the overview. For details on any part, and for step-by-step guides to adding tools, see [How Butler works](internals/README.md).

## Overview

```
 Web UI (React)      Telegram           Terminal
      │ HTTP + SSE       │ bot API           │ stdin
      ▼                  ▼                   ▼
 butler/web/       interfaces/         interfaces/
 (FastAPI)         telegram_bot.py     cli.py
      └──────────────────┼──────────────────┘
                         ▼
               butler/agent/graph.py        one LangGraph agent
              ┌──────────────────────┐
              │  agent (LLM) ⇄ tools │      loops until it can answer
              └──────────┬───────────┘
                         │ tool calls
          ┌──────────────┴───────────────┐
          ▼                              ▼
 integrations/gmail · calendar    integrations/swiggy/
 integrations/todos (SQLite)      Swiggy MCP servers (OAuth 2.1 + PKCE)
```

- **One agent, every tool.** There's no intent router. The LLM sees every tool and decides which ones to call, if any. A single message can use several tools ("unread mails *and* 15% of 240").
- **Pausing for the human.** When a tool needs a decision (pick an email, approve an order), it calls LangGraph's `interrupt(payload)`, and the graph stops. Each interface shows the question in its own way (numbered list, inline buttons, cards) and resumes with `Command(resume=answer)`. The shared logic lives in [`agent/human.py`](../butler/agent/human.py).
- **Agent memory.** A LangGraph checkpointer saves each conversation's working state (messages, tool calls, open questions) under a `thread_id`: one per Telegram chat, one per web conversation, one for the CLI session. It's `InMemorySaver`, so this is lost on restart.
- **Saved chats (web UI).** Separately, the web backend saves the sidebar list and the visible transcript (user and assistant text) in SQLite (`data/butler.db`), through `web/db/` (connection) and `web/repos/` (queries), orchestrated by `ChatService`. Old chats stay readable after a restart even though the agent's memory starts fresh.
- **Resilience.** A failing tool returns an error message to the LLM instead of crashing (`ToolNode(handle_tool_errors=True)`). Tool calls left unanswered by an earlier crash are patched before each LLM call (`with_tool_results`).

## Code layout

```
butler/
├── __main__.py              # `python -m butler <command>`
├── config.py                # .env settings, secret paths, time zone, startup checks
├── db/                      # shared SQLite connection (data/butler.db)
├── agent/
│   ├── graph.py             # builds the agent: tools, LLM, agent ⇄ tools loop, checkpointer
│   ├── prompts.py           # system prompt + one rules block per integration
│   └── human.py             # interrupt helpers shared by all interfaces
├── integrations/
│   ├── google_oauth.py      # shared Google login (Gmail, Calendar)
│   ├── gmail/               # auth, client, query builder, parser, tools.py, login.py
│   ├── calendar/            # auth, client, time helpers, tools.py (approvals), login.py
│   ├── todos/               # repo.py (table), service.py (rules), tools.py: local, no login
│   └── swiggy/              # MCP OAuth, MCP client, tools.py (approval wrappers), login.py
├── interfaces/
│   ├── cli.py               # terminal chat
│   ├── telegram_bot.py      # Telegram bot
│   └── web.py               # starts the web server
└── web/                     # FastAPI backend, layered:
    ├── app.py               #   app factory; serves /api and the built frontend
    ├── routes/              #   URL → handler registration only
    ├── handlers/            #   HTTP: validation, status codes, SSE streaming
    ├── services/            #   logic, no FastAPI: AgentService, ChatService, IntegrationService
    ├── repos/               #   data access: ThreadRepo, MessageRepo (+ chat tables)
    ├── schemas/             #   request/response models (Pydantic)
    ├── core/security.py     #   optional password protection
    └── dependencies.py      #   FastAPI dependency providers
frontend/                    # React + Vite + TypeScript web UI
```

## Deep dives

Each part has its own page under [internals/](internals/README.md):

| Topic | Page |
|---|---|
| One message through every layer | [Request lifecycle](internals/request-lifecycle.md) |
| The agent loop, prompt and model | [The agent](internals/agent.md) |
| Agent memory vs saved chats | [Memory](internals/memory.md) |
| How tools and MCP work | [Tools](internals/tools.md) |
| Adding tools, integrations and MCP servers | [Adding tools](internals/adding-tools.md) |
| Pickers and approvals | [Human in the loop](internals/human-in-the-loop.md) |
| Word-by-word replies in the web UI | [Streaming](internals/streaming.md) |
| Logins, tokens and access control | [Auth and security](internals/auth-and-security.md) |

## Development

```bash
pip install -e .
python -m butler web                 # API + built UI on :8000
cd frontend && npm run dev           # UI with hot reload on :5173 (proxies /api)
cd frontend && npm run build         # type-check + production build
```
