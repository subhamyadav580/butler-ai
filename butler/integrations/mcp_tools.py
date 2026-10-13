"""Helpers for LangChain tools that come from remote MCP servers (Swiggy, Zepto, …)."""

import json


def to_text(result):
    """MCP results come back as content blocks: [{"type": "text", "text": ...}]."""
    if isinstance(result, list):
        return "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in result
        )
    return str(result)


TOP_LEVEL_COMBINATORS = ("anyOf", "oneOf", "allOf")


def openai_compatible(schema):
    """OpenAI rejects anyOf/oneOf/allOf at the top level of a tool schema.

    Some servers use them for "addressId OR latitude+longitude". Drop them
    from the schema and state the rule in the description instead; the
    server still validates it. Returns (schema, text to append to the
    tool's description).
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


# Prepended to grocery apps' product-search tools. Their own descriptions say
# things like "MANDATORY FIRST STEP", which would otherwise beat Butler's
# rules about asking for the address and comparing apps first.
GROCERY_SEARCH_NOTE = (
    "[Butler] Use only after the user has chosen the delivery address in this "
    "conversation (ask first). If the user wants groceries without naming an "
    "app and search_groceries is available, use that instead of this "
    "tool.\n\n"
)
