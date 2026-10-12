"""Shared handling for interrupts, where the agent pauses for the human.

Tools pause the graph with interrupt(payload); payload["type"] says what is
being asked. Interfaces (CLI, Telegram, web) show the question and resume
with Command(resume=<answer>).
"""

from langgraph.types import Command

# Resume values that mean "the user moved on without answering"
CANCEL_ANSWERS = {
    "pick_email": {"email_id": None},
    "confirm_action": {"approved": False},
}


def pending_interrupt(graph, config):
    """Return the payload if this thread is paused waiting for the human."""
    state = graph.get_state(config)
    if state.interrupts:
        return state.interrupts[0].value
    return None


async def cancel_pending(graph, config):
    """Answer every open question with 'cancel' so a new message can run."""
    payload = pending_interrupt(graph, config)
    while payload:
        await graph.ainvoke(Command(resume=CANCEL_ANSWERS[payload["type"]]), config)
        payload = pending_interrupt(graph, config)



SWIGGY_PREFIXES = ("food_", "instamart_", "dineout_")


def show_raw_args(payload):
    """Whether an approval should show the tool's raw arguments.

    Calendar and todo approvals carry a readable summary in `details`, so the
    raw JSON is noise. Swiggy's arguments hold things the summary lacks
    (payment method, address id), so they stay visible.
    """
    if not payload.get("details"):
        return bool(payload.get("args"))
    return str(payload.get("tool", "")).startswith(SWIGGY_PREFIXES)
