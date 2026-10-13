from typing import Optional

from langchain_core.tools import tool
from langgraph.config import get_config

from . import service

NOT_ALLOWED = "Grocery apps are not available for this user."


def _allowed():
    return get_config().get("configurable", {}).get("allow_restricted", True)


@tool
async def grocery_addresses() -> str:
    """List the user's saved delivery addresses in every connected grocery app
    (Instamart, Zepto), so you can ask which one to deliver to."""
    if not _allowed():
        return NOT_ALLOWED
    return await service.list_addresses()


@tool
async def search_groceries(items: list[str], address: str, apps: Optional[list[str]] = None) -> str:
    """Search grocery apps (Swiggy Instamart, Zepto) for products at the user's
    delivery address. With no `apps`, searches every connected app and puts
    their products, pack sizes, prices and per-unit prices side by side for
    comparison. Read-only: nothing is added to any cart. This is the ONLY
    way to search grocery products.

    Args:
        items: Product names, one per item, normalised for search:
            ["amul taaza milk 1 litre", "brown bread", "eggs 12"].
        address: The delivery address THE USER chose in this conversation: a
            saved label ("Home", "RK", "Office") or part of the address
            ("Sector 28"). If the user hasn't said, don't guess: call
            grocery_addresses and ask them first.
        apps: Only these apps, when the user named one: ["zepto"] or
            ["instamart"]. Leave empty to compare all.
    """
    if not _allowed():
        return NOT_ALLOWED
    return await service.search(items, address, apps)


GROCERY_TOOLS = [grocery_addresses, search_groceries]
