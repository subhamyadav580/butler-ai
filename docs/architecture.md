# Architecture

This page explains how Butler works and how to add a new integration.

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
 integrations/gmail/             integrations/swiggy/
 Google API (read-only)          Swiggy MCP server (OAuth 2.1 + PKCE)
```

- **One agent, every tool.** There's no intent router. The LLM sees every tool and decides which ones to call, if any. A single message can use several tools ("unread mails *and* 15% of 240").
- **Pausing for the human.** When a tool needs a decision (pick an email, approve an order), it calls LangGraph's `interrupt(payload)`, and the graph stops. Each interface shows the question in its own way (numbered list, inline buttons, cards) and resumes with `Command(resume=answer)`. The shared logic lives in [`agent/human.py`](../butler/agent/human.py).
- **Memory.** A LangGraph checkpointer saves each conversation under a `thread_id`: one per Telegram chat, one per web conversation, one for the CLI session. It's `InMemorySaver` today; swap in a SQLite or Postgres checkpointer to survive restarts.
- **Resilience.** A failing tool returns an error message to the LLM instead of crashing (`ToolNode(handle_tool_errors=True)`). Tool calls left unanswered by an earlier crash are patched before each LLM call (`with_tool_results`).

## Code layout

```
butler/
├── __main__.py              # `python -m butler <command>`
├── config.py                # .env settings, secret paths, startup checks
├── agent/
│   ├── graph.py             # builds the agent: tools, LLM, agent ⇄ tools loop, checkpointer
│   ├── prompts.py           # system prompt + one rules block per integration
│   └── human.py             # interrupt helpers shared by all interfaces
├── integrations/
│   ├── gmail/               # auth, client, query builder, parser, tools.py, login.py
│   └── swiggy/              # MCP OAuth, MCP client, tools.py (approval wrappers), login.py
├── interfaces/
│   ├── cli.py               # terminal chat
│   ├── telegram_bot.py      # Telegram bot
│   └── web.py               # starts the web server
└── web/                     # FastAPI backend, layered:
    ├── app.py               #   app factory; serves /api and the built frontend
    ├── routes/              #   URL → handler registration only
    ├── handlers/            #   HTTP: validation, status codes, SSE streaming
    ├── services/            #   logic, no FastAPI: AgentService, IntegrationService
    ├── schemas/             #   request/response models (Pydantic)
    ├── core/security.py     #   optional password protection
    └── dependencies.py      #   FastAPI dependency providers
frontend/                    # React + Vite + TypeScript web UI
```

## Adding an integration

Say you want to add Google Calendar.

1. **Create `butler/integrations/calendar/`** with:
   - `config.py`: scopes, token path (add the path to `butler/config.py`)
   - `auth.py` and `login.py`: the login flow. Follow the Gmail pattern: never open a browser unless `interactive=True`, so a chat can't hang waiting for a login.
   - `tools.py`: LangChain tools (`@tool`) plus a `CALENDAR_TOOLS` list
2. **Register the tools** in `butler/agent/graph.py`: `all_tools = GMAIL_TOOLS + CALENDAR_TOOLS + swiggy_tools`.
3. **Add rules** in `butler/agent/prompts.py`: a short `CALENDAR_RULES` block on when and how to use the tools.
4. **Add a login command** in `butler/__main__.py` (`calendar-login`).
5. **Show it in the web UI:** add a status entry and a connect flow in `butler/web/services/integration_service.py`.
6. **Gate risky actions:** if a tool changes something (creates or deletes events), wrap it the way `swiggy/tools.py` does, calling `interrupt({"type": "confirm_action", ...})` before acting. Every interface already knows how to show `confirm_action`.
7. **Document it** in `docs/integrations/calendar.md`, and link it from the README.

A new **kind** of question (beyond `pick_email` and `confirm_action`) needs a renderer in each interface: `cli.py`, `telegram_bot.py`, and a component in `frontend/src/components/`. Also add a cancel value in `agent/human.py`.

## Development

```bash
pip install -e .
python -m butler web                 # API + built UI on :8000
cd frontend && npm run dev           # UI with hot reload on :5173 (proxies /api)
cd frontend && npm run build         # type-check + production build
```
