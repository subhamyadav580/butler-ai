import json

from langchain_core.tools import StructuredTool
from langgraph.config import get_config
from langgraph.types import interrupt

from .auth import SwiggyLoginRequired
from .client import get_swiggy_tools
from .config import LOGIN_COMMAND


# Tools that change something real on the user's Swiggy account
NEEDS_APPROVAL = {
    "place_food_order",
    "confirm_order",
    "create_address",
    "delete_address",
    "flush_food_cart",
}

# Shown alongside the approval prompt so the user sees what they're ordering
SHOW_CART_FOR = {"place_food_order", "confirm_order"}

LOGIN_EXPIRED = (
    "Swiggy login has expired. Tell the user to run "
    f"`{LOGIN_COMMAND}` on the machine running the assistant."
)

NOT_ALLOWED = "Swiggy is not available for this user."


def _is_login_error(error):
    if isinstance(error, SwiggyLoginRequired):
        return True
    return any(_is_login_error(e) for e in getattr(error, "exceptions", []))


def _swiggy_allowed():
    # Set per request by the caller, e.g. Telegram restricts it to the owner
    return get_config().get("configurable", {}).get("swiggy_allowed", True)


async def _call(tool, args):
    try:
        result = await tool.ainvoke(args)
    except Exception as error:
        if _is_login_error(error):
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


def _wrap(tool, cart_tool):
    async def run(**args):
        if not _swiggy_allowed():
            return NOT_ALLOWED

        if tool.name in NEEDS_APPROVAL:
            cart = None
            # get_food_cart requires addressId; both order tools carry it
            if tool.name in SHOW_CART_FOR and cart_tool and args.get("addressId"):
                cart = await _call(cart_tool, {"addressId": args["addressId"]})

            # Pause the graph; the caller resumes with {"approved": bool}.
            # On resume this function re-runs from the top, so nothing
            # above this line may change anything.
            answer = interrupt({
                "type": "confirm_action",
                "question": f"Allow Swiggy to run {tool.name}?",
                "tool": tool.name,
                "args": args,
                "details": cart,
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
    try:
        tools = await get_swiggy_tools(interactive=False)
    except Exception as error:
        if _is_login_error(error):
            return [], f"Swiggy not logged in — run: {LOGIN_COMMAND}"
        return [], f"Swiggy unavailable: {error!r}"

    cart_tool = next((t for t in tools if t.name == "get_food_cart"), None)
    return [_wrap(tool, cart_tool) for tool in tools], None
