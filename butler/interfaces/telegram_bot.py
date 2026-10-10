"""Telegram front-end for the agent."""

import logging

from langgraph.types import Command
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from butler.agent import build_graph, cancel_pending, pending_interrupt
from butler.config import (
    TELEGRAM_ALLOWED_USER_IDS as ALLOWED_USER_IDS,
    TELEGRAM_BOT_TOKEN as TOKEN,
    TELEGRAM_OWNER_ID as OWNER_ID,
)
from butler.integrations.swiggy import format_args

TELEGRAM_MAX_CHARS = 4096
PICK_PREFIX = "pick:"
PICK_CANCEL = "cancel"
CONFIRM_PREFIX = "confirm:"

# Built in post_init (loading Swiggy's MCP tools is async)
graph = None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def can_use_swiggy(user):
    # No owner configured: Swiggy is open to every allowed user
    if not OWNER_ID:
        return True
    return user is not None and user.id == OWNER_ID


def graph_config(update: Update):
    return {
        "configurable": {
            # One LangGraph thread (conversation memory) per Telegram chat
            "thread_id": f"telegram-{update.effective_chat.id}",
            "swiggy_allowed": can_use_swiggy(update.effective_user),
        }
    }


async def is_allowed(update: Update):
    # No allow-list configured: open to everyone
    if not ALLOWED_USER_IDS:
        return True

    user = update.effective_user
    if user and user.id in ALLOWED_USER_IDS:
        return True

    await update.effective_message.reply_text(
        "Sorry, you're not allowed to use this bot.\n"
        f"Your Telegram user id is {user.id if user else 'unknown'} — add it "
        "to TELEGRAM_ALLOWED_USER_IDS in .env to get access."
    )
    return False


async def send_text(message, text):
    text = text or "(no response)"
    for start in range(0, len(text), TELEGRAM_MAX_CHARS):
        await message.reply_text(text[start:start + TELEGRAM_MAX_CHARS])


async def send_pick_list(message, payload):
    emails = payload["emails"]

    lines = [payload["question"], ""]
    buttons = []
    for i, email in enumerate(emails, start=1):
        marker = "● " if email["unread"] else ""
        lines.append(f"{i}. {marker}{email['from']}\n    {email['subject']}")
        buttons.append([
            InlineKeyboardButton(
                f"{i}. {email['subject'][:40] or '(no subject)'}",
                callback_data=f"{PICK_PREFIX}{email['id']}",
            )
        ])
    buttons.append([
        InlineKeyboardButton("Cancel", callback_data=f"{PICK_PREFIX}{PICK_CANCEL}")
    ])

    await message.reply_text(
        "\n".join(lines)[:TELEGRAM_MAX_CHARS],
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def send_confirm(message, payload):
    text = f"⚠️ {payload['question']}\n\n{format_args(payload['args'])}"
    if payload.get("details"):
        text += f"\n\n{payload['details']}"

    await message.reply_text(
        text[:TELEGRAM_MAX_CHARS],
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"{CONFIRM_PREFIX}yes"),
            InlineKeyboardButton("❌ Reject", callback_data=f"{CONFIRM_PREFIX}no"),
        ]]),
    )


HUMAN_PROMPTS = {
    "pick_email": send_pick_list,
    "confirm_action": send_confirm,
}


async def run_agent(message, graph_input, config):
    """Run the graph, then either reply or ask the human a question."""
    await message.chat.send_action(ChatAction.TYPING)

    result = await graph.ainvoke(graph_input, config)

    if result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        await HUMAN_PROMPTS[payload["type"]](message, payload)
    else:
        await send_text(message, result["messages"][-1].content)


def typed_answer(payload, text):
    """Let users answer a pending question by typing instead of tapping."""
    text = text.strip().lower()

    if payload["type"] == "pick_email":
        emails = payload["emails"]
        if text.isdigit() and 1 <= int(text) <= len(emails):
            return {"email_id": emails[int(text) - 1]["id"]}

    if payload["type"] == "confirm_action":
        if text in ("yes", "y", "approve"):
            return {"approved": True}
        if text in ("no", "n", "reject"):
            return {"approved": False}

    return None


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update):
        return

    examples = (
        "• show my latest 5 mails in updates\n"
        "• how many unread promotions do I have?\n"
        "• open a mail from LinkedIn\n"
    )
    if can_use_swiggy(update.effective_user):
        examples += "• find biryani near my office on Swiggy\n"

    await update.message.reply_text(
        "Hi! Ask me anything, or about your Gmail — e.g.\n"
        f"{examples}\n"
        "/reset clears our conversation memory.\n\n"
        f"Your Telegram user id: {update.effective_user.id}"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update):
        return

    graph.checkpointer.delete_thread(graph_config(update)["configurable"]["thread_id"])
    await update.message.reply_text("Memory cleared. Starting fresh.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update):
        return

    text = update.message.text
    config = graph_config(update)

    print("Received:", text)

    payload = pending_interrupt(graph, config)
    if payload:
        answer = typed_answer(payload, text)
        if answer:
            await run_agent(update.message, Command(resume=answer), config)
            return

    # Anything else: cancel open questions, then handle the new message
    await cancel_pending(graph, config)

    await run_agent(
        update.message,
        {"messages": [{"role": "user", "content": text}]},
        config,
    )


async def handle_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_allowed(update):
        return

    config = graph_config(update)
    payload = pending_interrupt(graph, config)

    # Stale button from an older list
    if not payload or payload["type"] != "pick_email":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("That list has expired — ask again.")
        return

    choice = query.data.removeprefix(PICK_PREFIX)
    chosen_id = None if choice == PICK_CANCEL else choice

    # Remove the buttons so the same list can't be answered twice
    picked = next(
        (e["subject"] for e in payload["emails"] if e["id"] == chosen_id),
        None,
    )
    await query.edit_message_text(
        f"Opening: {picked}" if picked else "Cancelled."
    )

    await run_agent(
        query.message,
        Command(resume={"email_id": chosen_id}),
        config,
    )


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # In group chats anyone could tap the button; only Swiggy users may approve
    if not await is_allowed(update) or not can_use_swiggy(update.effective_user):
        await query.message.reply_text("You can't approve Swiggy actions.")
        return

    config = graph_config(update)
    payload = pending_interrupt(graph, config)

    if not payload or payload["type"] != "confirm_action":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("That request has expired — ask again.")
        return

    approved = query.data.removeprefix(CONFIRM_PREFIX) == "yes"

    # Replace the buttons so the same request can't be answered twice
    await query.edit_message_text(
        f"{'✅ Approved' if approved else '❌ Rejected'}: {payload['tool']}"
    )

    await run_agent(
        query.message,
        Command(resume={"approved": approved}),
        config,
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Log the full traceback, but tell the user instead of going silent
    logging.error("Error while handling an update", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. Try again, or send /reset to "
            "start a fresh conversation."
        )


async def post_init(app: Application):
    global graph
    graph = await build_graph()


def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set in .env")

    if not ALLOWED_USER_IDS:
        print(
            "WARNING: TELEGRAM_ALLOWED_USER_IDS is empty — anyone who finds "
            "this bot can use it and read your Gmail."
        )
    if not OWNER_ID:
        print(
            "WARNING: TELEGRAM_OWNER_ID is not set — every allowed user can "
            "use Swiggy on your account."
        )

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_error_handler(on_error)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(handle_pick, pattern=f"^{PICK_PREFIX}"))
    app.add_handler(CallbackQueryHandler(handle_confirm, pattern=f"^{CONFIRM_PREFIX}"))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()
