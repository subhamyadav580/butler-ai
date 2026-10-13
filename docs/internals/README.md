# How Butler works

These pages explain Butler's internals for contributors, and for anyone who wants to change or extend it. For installing and using Butler, start with [Getting started](../getting-started.md) instead.

## The big picture

```
  Web UI          Telegram          Terminal            ← interfaces
     │                │                 │
     └────────────────┼─────────────────┘
                      ▼
            ┌───────────────────┐
            │      agent        │  one LLM + every tool   ← agent
            │  (LangGraph loop) │  memory per thread_id
            └─────────┬─────────┘
                      │ tool calls
          ┌───────────┴────────────┐
          ▼                        ▼
       Gmail                  Swiggy, Zepto (MCP)       ← integrations
```

Butler is **one LangGraph agent** that every interface shares. The interfaces only translate between their medium (HTTP, Telegram updates, stdin) and the agent. The integrations only expose **LangChain tools**. Everything interesting happens in the loop between the LLM and those tools.

## Pages

| Page | Read it to understand |
|---|---|
| [Request lifecycle](request-lifecycle.md) | What happens, step by step, from "you hit Enter" to "the reply appears" |
| [The agent](agent.md) | The agent ⇄ tools loop, the system prompt, model choice, and error handling |
| [Memory](memory.md) | Agent memory (the context sent to the LLM) vs saved chats (the database), and what survives a restart |
| [Tools](tools.md) | How tools are defined and loaded: plain Python tools (Gmail) and MCP tools (Swiggy, Zepto) |
| [Adding tools](adding-tools.md) | Step-by-step recipes: a new tool, a new integration, a new MCP server |
| [Human in the loop](human-in-the-loop.md) | How the email picker and Approve/Reject pause and resume the agent |
| [Streaming](streaming.md) | How the web UI receives replies word by word (HTTP + Server-Sent Events) |
| [Auth and security](auth-and-security.md) | How accounts are connected, where tokens live, and who may use what |

## Where things live

```
butler/
├── agent/          graph.py (the loop) · prompts.py (assembles sections) · human.py (interrupt helpers) · stream.py (live events)
├── integrations/   base.py (the contract) · registry.py (the list) · gmail/ · calendar/ · todos/ · websearch/ · swiggy/ · zepto/ · groceries/ · mcp_oauth.py
│                   each with an integration.py: tools, prompt rules, status, login, UI labels
├── db/             shared SQLite connection (chats, todos)
├── interfaces/     cli.py · telegram_bot.py · web.py
├── web/            FastAPI: routes → handlers → services → repos → db
└── config.py       settings from .env
frontend/           React UI
```

## Key ideas in one paragraph

The agent is a two-node graph: `agent` (the LLM) and `tools` (runs whatever the LLM asked for). The two loop until the LLM answers in plain text. Every step is saved by a **checkpointer** under the conversation's `thread_id`; that saved message list *is* the agent's memory, and it's re-sent to the LLM on every turn. A tool can **pause** the whole graph with `interrupt()` to ask the human something (which email? approve this order?). The interface shows the question and **resumes** the graph with the answer. The web UI streams the run to the browser as Server-Sent Events and saves the visible transcript to SQLite, so chats survive restarts even though agent memory doesn't.
