"""Zepto's MCP tools, wrapped with the owner check and human approval."""

import re

from langchain_core.tools import StructuredTool
from langgraph.config import get_config
from langgraph.types import interrupt

from butler.integrations.mcp_oauth import describe_error, is_login_error
from butler.integrations.mcp_tools import GROCERY_SEARCH_NOTE, openai_compatible, to_text

from .auth import storage
from .client import get_zepto_tools
from .config import LOGIN_COMMAND, SERVER_NAME

PREFIX = SERVER_NAME + "_"
PREVIEW_CHARS = 1500

# The unwrapped Zepto tools of the running agent, by name: other integrations
# (groceries' price comparison) call read-only ones directly
RAW_TOOLS = {}

LOGIN_EXPIRED = (
    "Zepto login has expired. Tell the user to run "
    f"`{LOGIN_COMMAND}` on the machine running the assistant."
)
NOT_ALLOWED = "Zepto is not available for this user."

# zepto_shop only opens ChatGPT's shopping widget (its own description says
# not to use it from other clients)
EXCLUDED_TOOLS = {"zepto_zepto_shop"}

# Placing an order. Each takes confirmOrder: false returns a preview (nothing
# is ordered), true places the order. Only true needs the user's Approve, and
# the card shows the preview.
ORDER_TOOLS = {
    "zepto_create_order": "Place this Zepto order (cash on delivery)?",
    "zepto_create_online_payment_order": "Place this Zepto order and pay online (UPI/card link)?",
    "zepto_create_wallet_order": "Place this Zepto order, paid with Zepto Cash?",
    "zepto_create_upi_reserve_pay_order": "Place this Zepto order with UPI Reserve Pay?",
}

# Other changes to the account
NEEDS_APPROVAL = {
    "zepto_add_saved_address": "Add this address to your Zepto account?",
    "zepto_update_user_name": "Change your name on Zepto?",
}

# Known tools that run without asking: reads, choosing the address/store for
# this session, and cart edits (nothing is charged until an order is placed)
NO_APPROVAL = {
    "zepto_search_products", "zepto_search_multiple_products", "zepto_get_product_details",
    "zepto_get_location_serviceability", "zepto_select_store", "zepto_list_saved_addresses",
    "zepto_select_saved_address", "zepto_update_drop_zone", "zepto_get_user_details",
    "zepto_view_cart", "zepto_update_cart", "zepto_get_payment_methods",
    "zepto_check_payment_status", "zepto_get_order_detail", "zepto_list_order_history",
    "zepto_get_past_order_items",
}

# A tool Zepto adds later is decided by its name: reads run, anything else asks
READ_VERBS = ("get", "list", "search", "find", "view", "show", "fetch", "lookup", "track", "check")


def needs_approval(tool):
    if tool.name in ORDER_TOOLS or tool.name in NEEDS_APPROVAL:
        return True
    if tool.name in NO_APPROVAL:
        return False
    return tool.name.removeprefix(PREFIX).split("_")[0] not in READ_VERBS


def approval_question(tool):
    return (
        ORDER_TOOLS.get(tool.name)
        or NEEDS_APPROVAL.get(tool.name)
        or f"Zepto: {tool.name.removeprefix(PREFIX).replace('_', ' ')}?"
    )


def _allowed():
    # Telegram allows restricted integrations (like Zepto) only for the owner
    return get_config().get("configurable", {}).get("allow_restricted", True)


def _device_id():
    # update_cart needs a stable device ID; the client ID Zepto registered for
    # this Butler install is one, so the model never has to invent it
    return storage().client_id() or "butler"


async def _call(tool, args):
    try:
        return to_text(await tool.ainvoke(args))
    except Exception as error:
        if is_login_error(error):
            return LOGIN_EXPIRED
        raise


def _asks_now(tool, args):
    if tool.name in ORDER_TOOLS:
        return args.get("confirmOrder") is True       # a preview orders nothing
    return needs_approval(tool)


async def _preview(tool, args, raw):
    """What the approval card shows (Markdown). Read-only: this runs again
    when the graph resumes."""
    if tool.name not in ORDER_TOOLS:
        return None
    # The same tool with confirmOrder=false: Zepto's own order preview
    preview = await _call(tool, {**args, "confirmOrder": False})
    # It lists items by product ID only; the cart has their names and prices
    if "zepto_view_cart" in raw:
        names = _cart_names(await _call(raw["zepto_view_cart"], {}))
        for product_id, name in names.items():
            preview = preview.replace(product_id, name)
    return _for_people(preview)


def _for_people(text):
    """The preview as the user should see it: without Zepto's instructions to
    the AI ("Confirmation Required: … call again with confirmOrder: true"),
    with its line breaks kept (Markdown would join single lines)."""
    paragraphs = [p for p in text.split("\n\n") if "confirmOrder" not in p and "SYSTEM" not in p]
    return "\n\n".join(paragraphs).strip().replace("\n", "  \n").replace("  \n  \n", "\n\n")


# "1. Mother Dairy Promilk | Pouch - ₹36 (Qty: 1)\n   pvid: 49d4…, spid: …"
CART_LINE = re.compile(r"^\s*\d+\.\s+(.+?)\s+\(Qty:.*?\)\s*\n\s*pvid:\s*([\w-]+)", re.MULTILINE)


def _cart_names(cart_text):
    """{product variant ID: "name - price"} from zepto_view_cart's text."""
    return {product_id: name for name, product_id in CART_LINE.findall(cart_text)}


def _wrap(tool, raw):
    hidden = {"deviceId"} if tool.name == "zepto_update_cart" else set()

    async def run(**args):
        if not _allowed():
            return NOT_ALLOWED
        if hidden:
            args["deviceId"] = _device_id()

        if _asks_now(tool, args):
            try:
                details = await _preview(tool, args, raw)
            except Exception:  # noqa: BLE001 — a preview must never block approval
                details = None

            # Pause the graph; the caller resumes with {"approved": bool}.
            # On resume this function re-runs from the top, so nothing
            # above this line may change anything.
            answer = interrupt({
                "type": "confirm_action",
                "question": approval_question(tool),
                "tool": tool.name,
                "args": {k: v for k, v in args.items() if k not in hidden},
                "details": details[:PREVIEW_CHARS] if details else None,
                "restricted": True,   # only the owner may approve (Telegram)
                "show_args": not details,
                "details_markdown": True,
            })
            if not (answer or {}).get("approved"):
                return (
                    f"The user rejected {tool.name}. Nothing was changed. "
                    "Ask what they would like to do instead."
                )

        return await _call(tool, args)

    schema, extra_rules = openai_compatible(_without(tool.args_schema, hidden))
    return StructuredTool.from_function(
        coroutine=run,
        name=tool.name,
        description=_description(tool) + extra_rules,
        args_schema=schema,
    )


SEARCH_TOOLS = {"zepto_search_products", "zepto_search_multiple_products"}


# Zepto's own text says to call this before every search; Butler uses it only
# when asked about usual items
DESCRIPTIONS = {
    "zepto_get_past_order_items": (
        "Products the user has ordered on Zepto before (last 30+ orders), most "
        "frequent first. Use when the user asks for their usual or past Zepto items."
    ),
}


def _description(tool):
    text = DESCRIPTIONS.get(tool.name, tool.description or "")
    return GROCERY_SEARCH_NOTE + text if tool.name in SEARCH_TOOLS else text


def _without(schema, fields):
    """The schema minus fields Butler fills in itself."""
    if not fields:
        return schema
    return {
        **schema,
        "properties": {k: v for k, v in schema.get("properties", {}).items() if k not in fields},
        "required": [k for k in schema.get("required", []) if k not in fields],
    }


async def load_zepto_tools():
    """(tools, problem). Returns [] and the reason if Zepto isn't logged in,
    so the rest of the agent still works."""
    if not storage().has_tokens():
        return [], f"Zepto not connected — run: {LOGIN_COMMAND}"
    try:
        tools = await get_zepto_tools(interactive=False)
    except Exception as error:
        if is_login_error(error):
            return [], f"Zepto login expired — run: {LOGIN_COMMAND}"
        return [], f"Zepto unavailable: {describe_error(error)}"

    tools = [tool for tool in tools if tool.name not in EXCLUDED_TOOLS]
    raw = {tool.name: tool for tool in tools}
    RAW_TOOLS.clear()
    RAW_TOOLS.update(raw)
    return [_wrap(tool, raw) for tool in tools], None
