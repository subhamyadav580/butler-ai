"""Shared handling for interrupts, where the agent pauses for the human.

Tools pause the graph with interrupt(payload); payload["type"] says what is
being asked. Interfaces (CLI, Telegram, web) show the question and resume
with Command(resume=<answer>).
"""

import json

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



def show_raw_args(payload):
    """Whether an approval card should also show the tool's raw arguments.

    Tools decide: a payload with "show_args": True always shows them (Swiggy
    sets it: payment method, address id). Otherwise only when there's no
    readable `details` summary.
    """
    if payload.get("show_args"):
        return bool(payload.get("args"))
    return not payload.get("details") and bool(payload.get("args"))


def is_restricted(payload):
    """Approvals marked "restricted" act on the owner's account (orders,
    payments): only users allowed restricted integrations may answer them."""
    return bool(payload.get("restricted"))


def format_args(args):
    """Tool arguments as readable JSON, for approval prompts."""
    return json.dumps(args, indent=2, ensure_ascii=False)
