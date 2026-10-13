"""App-neutral types for grocery comparison.

Every grocery app (Instamart, Zepto, …) turns its own MCP results into these,
so the comparison never depends on one app's JSON shape.
"""

from dataclasses import dataclass, field
from typing import Optional


class GroceryError(Exception):
    """An app failed (login expired, rate limit, address not serviceable)."""


@dataclass
class Address:
    app: str                 # "instamart"
    id: str
    label: str               # "Home", "RK", "work"
    text: str                # full address line
    postal_code: Optional[str] = None


@dataclass
class Offer:
    app: str
    name: str
    pack: str                # "500 ml x 4", "1 pack (1 L)"
    price: float             # rupees, what you pay
    mrp: Optional[float]
    in_stock: bool
    ids: dict = field(default_factory=dict)   # what the app's cart tool needs


class GroceryProvider:
    name = ""                # "instamart"
    title = ""               # "Swiggy Instamart"
    order_hint = ""          # how to add to cart and order with this app's tools
    search_tools: set[str] = set()   # the app's own product search, replaced by search_groceries

    def available(self) -> bool:
        """True when the app's tools are loaded in the running agent."""
        raise NotImplementedError

    async def addresses(self) -> list[Address]:
        raise NotImplementedError

    async def prepare(self, address: Address):
        """Anything to do once before searching (e.g. choose the store)."""

    async def search(self, query: str, address: Address) -> list[Offer]:
        raise NotImplementedError


async def structured(tool, args):
    """Call an MCP tool and return its structured result (the JSON the app
    sends alongside its text)."""
    message = await tool.ainvoke({"type": "tool_call", "name": tool.name, "args": args, "id": "groceries"})
    data = (message.artifact or {}).get("structured_content")
    if data is None:
        raise GroceryError(str(message.content)[:300])
    return data
