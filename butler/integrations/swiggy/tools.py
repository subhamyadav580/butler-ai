import json
import time
from datetime import datetime

from langchain_core.tools import StructuredTool
from langgraph.config import get_config
from langgraph.types import interrupt

from .auth import FileTokenStorage, describe_error, is_login_error
from .client import get_swiggy_tools
from .config import LOGIN_COMMAND


# Tools that change something real on the user's Swiggy account, with the
# question shown on the Approve/Reject card. Names carry the service prefix.
NEEDS_APPROVAL = {
    # Food
    "food_place_food_order": "Place this Swiggy Food order?",
    "food_confirm_order": "Confirm this Swiggy Food order?",
    "food_create_address": "Add this address to your Swiggy account?",
    "food_delete_address": "Delete this saved Swiggy address?",
    "food_flush_food_cart": "Clear your Swiggy Food cart?",
    # Instamart
    "instamart_checkout": "Place this Instamart order?",
    "instamart_confirm_order": "Confirm this Instamart order?",
    "instamart_create_address": "Add this address to your Swiggy account?",
    "instamart_delete_address": "Delete this saved Swiggy address?",
    "instamart_clear_cart": "Clear your Instamart cart?",
    # Dineout
    "dineout_book_table": "Book this table on Swiggy Dineout?",
    "dineout_confirm_order": "Confirm this Dineout booking payment?",
}

PREVIEW_CHARS = 1500

LOGIN_EXPIRED = (
    "Swiggy login has expired. Tell the user to run "
    f"`{LOGIN_COMMAND}` on the machine running the assistant."
)

NOT_ALLOWED = "Swiggy is not available for this user."


def _swiggy_allowed():
    # Set per request by the caller, e.g. Telegram restricts it to the owner
    return get_config().get("configurable", {}).get("swiggy_allowed", True)


async def _call(tool, args):
    try:
        result = await tool.ainvoke(args)
    except Exception as error:
        if is_login_error(error):
            return LOGIN_EXPIRED
        raise
    return _strip_widget_notes(_to_text(result))


def _to_text(result):
    # MCP results come back as content blocks: [{"type": "text", "text": ...}]
    if isinstance(result, list):
        return "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in result
        )
    return str(result)


# Swiggy assumes a client that renders a cart/address "widget" and tells the
# LLM not to repeat what the widget shows. Telegram and the CLI have no
# widget, so those instructions would hide the cart from the user.
WIDGET_HINTS = ("widget", "stepper", "Confirm and Review Cart")


def _strip_widget_notes(text):
    return "\n".join(
        line for line in text.splitlines()
        if not any(hint.lower() in line.lower() for hint in WIDGET_HINTS)
    ).strip()


async def _preview(name, args, raw):
    """What the approval card shows next to the question. Read-only calls only:
    this runs again when the graph resumes."""
    if name in ("food_place_food_order", "food_confirm_order") and args.get("addressId"):
        return await _call(raw["food_get_food_cart"], {"addressId": args["addressId"]})

    if name in ("instamart_checkout", "instamart_confirm_order") and "instamart_get_cart" in raw:
        return await _call(raw["instamart_get_cart"], {})

    if name == "dineout_book_table":
        when = args.get("reservationTime")
        lines = [
            f"Guests: {args.get('guestCount', '?')}",
            "Time: " + (
                datetime.fromtimestamp(int(when)).strftime("%a %d %b %Y, %I:%M %p")
                if when else "?"
            ),
            f"Payment: {args.get('paymentMethod') or 'free reservation'}",
        ]
        details = raw.get("dineout_get_restaurant_details")
        if details and args.get("latitude") is not None:
            text = await _call(details, {
                "restaurantId": args["restaurantId"],
                "latitude": args["latitude"],
                "longitude": args["longitude"],
            })
            lines += ["", text]
        return "\n".join(lines)

    return None


def _wrap(tool, raw):
    async def run(**args):
        if not _swiggy_allowed():
            return NOT_ALLOWED

        if tool.name in NEEDS_APPROVAL:
            try:
                details = await _preview(tool.name, args, raw)
            except Exception:  # noqa: BLE001 — a preview must never block approval
                details = None

            # Pause the graph; the caller resumes with {"approved": bool}.
            # On resume this function re-runs from the top, so nothing
            # above this line may change anything.
            answer = interrupt({
                "type": "confirm_action",
                "question": NEEDS_APPROVAL[tool.name],
                "tool": tool.name,
                "args": args,
                "details": details[:PREVIEW_CHARS] if details else None,
            })
            if not (answer or {}).get("approved"):
                return (
                    f"The user rejected {tool.name}. Nothing was changed. "
                    "Ask what they would like to do instead."
                )

        return await _call(tool, args)

    schema, extra_rules = _openai_compatible(tool.args_schema)

    return StructuredTool.from_function(
        coroutine=run,
        name=tool.name,
        description=tool.description + extra_rules,
        args_schema=schema,
    )


TOP_LEVEL_COMBINATORS = ("anyOf", "oneOf", "allOf")


def _openai_compatible(schema):
    """OpenAI rejects anyOf/oneOf/allOf at the top level of a tool schema.

    Swiggy uses them for "addressId OR latitude+longitude". Drop them from
    the schema and state the rule in the description instead; the Swiggy
    server still validates it.
    """
    if not any(key in schema for key in TOP_LEVEL_COMBINATORS):
        return schema, ""

    schema = dict(schema)
    rules = []
    for key in TOP_LEVEL_COMBINATORS:
        options = schema.pop(key, None)
        if not options:
            continue
        alternatives = [
            " + ".join(option.get("required", [])) or json.dumps(option)
            for option in options
        ]
        joiner = " AND " if key == "allOf" else " OR "
        rules.append(f"You must provide: {joiner.join(alternatives)}.")

    return schema, "\n\n" + " ".join(rules)


def format_args(args):
    return json.dumps(args, indent=2, ensure_ascii=False)


async def load_swiggy_tools():
    """Swiggy tools wrapped with access checks and human approval.

    Returns [] (and the reason) if Swiggy isn't logged in, so the rest of
    the agent still works.
    """
    # No saved (or an expired) login: skip the network round-trip, which
    # would only fail with a noisy OAuth traceback
    expires_at = FileTokenStorage().get_expires_at()
    if not expires_at or expires_at < time.time():
        return [], f"Swiggy not connected — run: {LOGIN_COMMAND}"

    failures = {}
    try:
        tools = await get_swiggy_tools(interactive=False, failures=failures)
    except Exception as error:
        if is_login_error(error):
            return [], f"Swiggy not logged in — run: {LOGIN_COMMAND}"
        return [], f"Swiggy unavailable: {describe_error(error)}"

    problem = None
    if failures:
        problem = "Swiggy " + "; ".join(
            f"{name} unavailable ({reason})" for name, reason in failures.items()
        )
        if not tools:
            return [], problem

    raw = {tool.name: tool for tool in tools}
    return [_wrap(tool, raw) for tool in tools], problem


def services_of(tools):
    """Which Swiggy services these tools belong to: {"food", "instamart", …}."""
    return {tool.name.split("_", 1)[0] for tool in tools}


# Read-only tools that prove a login works, in order of preference
SMOKE_TEST_TOOLS = ("food_get_addresses", "instamart_get_addresses", "dineout_get_saved_locations")


async def smoke_test(tools):
    """Call one harmless read-only tool; returns its text."""
    by_name = {tool.name: tool for tool in tools}
    for name in SMOKE_TEST_TOOLS:
        if name in by_name:
            return _to_text(await by_name[name].ainvoke({}))
    return "(no address tool among the enabled services)"
