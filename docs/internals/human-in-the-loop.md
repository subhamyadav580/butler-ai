# Human in the loop

Sometimes a tool needs a person: *which* email to open, or *may I* place this order? Butler handles this with LangGraph **interrupts**: the tool pauses the whole graph, the interface asks you, and the graph resumes with your answer from exactly where it stopped.

Code: [agent/human.py](../../butler/agent/human.py), the tools that raise interrupts ([gmail/tools.py](../../butler/integrations/gmail/tools.py) `pick_email`, and [swiggy/tools.py](../../butler/integrations/swiggy/tools.py) `_wrap`), and each interface.

## The two questions Butler asks today

| `type` | Raised by | Payload | Resume value |
|---|---|---|---|
| `pick_email` | `pick_email` tool | `question`, `emails: [{id, from, subject, snippet, unread, …}]` | `{"email_id": "<id>"}`, or `{"email_id": null}` to cancel |
| `confirm_action` | Swiggy tools in `NEEDS_APPROVAL` (Food, Instamart and Dineout orders, bookings, address changes, clearing carts) | `question` (for example "Book this table on Swiggy Dineout?"), `tool`, `args`, `details` (cart or booking preview) | `{"approved": true \| false}` |

## How a pause works

```python
# inside a tool
answer = interrupt({"type": "pick_email", "question": "...", "emails": emails})
```

1. **First run:** `interrupt()` raises a special signal. LangGraph stops the run and the **checkpointer** saves everything, including "the `tools` node is mid-way, waiting on this payload".
2. **The caller gets the question:**
   - `graph.ainvoke()` returns a result with `result["__interrupt__"][0].value == payload`
   - `graph.astream()` yields an `updates` chunk with `__interrupt__`
   - `graph.get_state(config).interrupts` also exposes it at any time
3. **The interface asks you.**
4. **Resume:** `graph.ainvoke(Command(resume=answer), config)`.
5. **Second run:** the tool **runs again from the top**. This time `interrupt()` *returns* `answer` instead of pausing, and the tool carries on.

> Because of step 5, anything a tool does **before** `interrupt()` runs twice. Keep that part read-only, and do irreversible work after it. That's why `pick_email` stores the **email ID** as the answer, not a list position: if a new mail arrives between the two runs, the list changes but the ID still opens the email you saw.

A checkpointer is **required** for interrupts; without one, LangGraph can't save the paused state.

## How each interface asks

| | Terminal | Telegram | Web |
|---|---|---|---|
| Email picker | Numbered list, `Pick a number:` (0 cancels) | Message plus one button per email and **Cancel**; typing the number works too | `<EmailPicker>` card |
| Approval | Action details, then `Approve? (y/n)` | **✅ Approve / ❌ Reject** buttons; typing `yes`/`no` works | `<ApprovalCard>` |
| Resume | `Command(resume=…)` directly | Button callback → `Command(resume=…)` | `POST /api/chat/resume` (streams the rest) |
| Code | `HUMAN_PROMPTS` in [cli.py](../../butler/interfaces/cli.py) | `HUMAN_PROMPTS`, `handle_pick`, `handle_confirm`, `typed_answer` in [telegram_bot.py](../../butler/interfaces/telegram_bot.py) | [Chat.tsx](../../frontend/src/components/Chat.tsx), [web/handlers/chat.py](../../butler/web/handlers/chat.py) |

Each interface keys its renderer on `payload["type"]`, so one table drives all of them.

## When the user moves on without answering

If a thread is paused and the user sends a **new message** instead:

```python
await cancel_pending(graph, config)    # agent/human.py
```

This resumes every open question with its **cancel value** from `CANCEL_ANSWERS`:

```python
CANCEL_ANSWERS = {
    "pick_email": {"email_id": None},
    "confirm_action": {"approved": False},   # moving on = reject
}
```

Then it runs the new message. Without this, the new message would start a fresh run on top of a half-finished one. That leaves an `AIMessage` with a tool call that never got a result, and OpenAI rejects such a history.

## What the LLM sees

The tool turns your answer into a normal tool result, so the LLM reacts naturally:

| Answer | Tool result |
|---|---|
| Picked an email | `{"status": "selected", "message": "The user picked this email. Present its details.", "email": {…}}` |
| Cancelled the picker | `{"status": "cancelled", "message": "The user closed the email picker on purpose. This is not an error: do not retry…"}` |
| Approved | The real Swiggy tool's result |
| Rejected | `"The user rejected food_place_food_order. Nothing was changed. Ask what they would like to do instead."` |

The wording matters: an earlier "User did not pick an email" made the model apologise and retry, as if something had failed.

## Safety guarantees

- **Approval comes before the call.** For gated tools, the real MCP call happens only after `approved: true`.
- **Rejection and silence are safe.** Rejecting, cancelling, or sending another message never runs the action.
- **Stale buttons do nothing.** Both Telegram and the web check that the thread is still waiting for *that kind* of question. Otherwise, Telegram says "expired" and the API returns `409`.
- **Group chats are covered.** In a Telegram group, only users allowed to use Swiggy can tap Approve.

To add a new kind of question, see [Adding tools: a new kind of question](adding-tools.md#6-add-a-new-kind-of-question).
