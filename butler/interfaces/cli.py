"""Terminal chat with the agent."""

import asyncio

from langgraph.types import Command

from butler.agent import build_graph
from butler.integrations.swiggy import format_args


def ask_user_to_pick(payload):
    """Show the emails from a pick_email interrupt; return the resume value."""
    emails = payload["emails"]

    print(f"\n{payload['question']}")
    for i, email in enumerate(emails, start=1):
        marker = "●" if email["unread"] else " "
        print(f"  {i:>2}. {marker} {email['from'][:30]:<30}  {email['subject'][:60]}")
    print("   0. Cancel")

    while True:
        choice = input("Pick a number: ").strip()
        if choice.isdigit() and 0 <= int(choice) <= len(emails):
            break
        print(f"Enter a number between 0 and {len(emails)}.")

    return {"email_id": emails[int(choice) - 1]["id"] if int(choice) else None}


def ask_user_to_confirm(payload):
    """Show a confirm_action interrupt; return the resume value."""
    print(f"\n⚠️  {payload['question']}")
    print(format_args(payload["args"]))
    if payload.get("details"):
        print(payload["details"])

    answer = input("Approve? (y/n): ").strip().lower()
    return {"approved": answer in ("y", "yes")}


HUMAN_PROMPTS = {
    "pick_email": ask_user_to_pick,
    "confirm_action": ask_user_to_confirm,
}


async def chat(graph, text, config):
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": text}]}, config
    )

    # Keep resuming while the graph is paused waiting for the human
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        answer = HUMAN_PROMPTS[payload["type"]](payload)
        result = await graph.ainvoke(Command(resume=answer), config)

    return result["messages"][-1].content


async def main():
    graph = await build_graph()
    config = {"configurable": {"thread_id": "cli", "swiggy_allowed": True}}

    print("Chat with your assistant (type 'exit' to quit)")
    while True:
        text = (await asyncio.to_thread(input, "\nYou: ")).strip()
        if text.lower() in ("exit", "quit"):
            break
        if text:
            print("AI:", await chat(graph, text, config))


if __name__ == "__main__":
    asyncio.run(main())
