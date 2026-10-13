"""Grocery price comparison across every connected grocery app (Swiggy
Instamart, Zepto). Uses the apps' own integrations for the actual ordering."""

from butler.integrations.base import Integration

from .registry import PROVIDERS, available_providers
from .tools import GROCERY_TOOLS

RULES = (
    "Groceries (Swiggy Instamart, Zepto): milk, bread, eggs, fruit, "
    "vegetables, snacks, cleaning and household items…\n"
    "1. Delivery address first. Before any grocery search or order, if the "
    "user hasn't said which address in this conversation, call "
    "grocery_addresses and ask which one to deliver to (show the labels). "
    "Never pick an address for them.\n"
    "2. Search ONLY with search_groceries, once, with every item and that "
    "address. If the user named an app (\"on Zepto\"), pass apps=[that "
    "app]; otherwise leave apps empty to compare every app.\n"
    "3. When comparing, show for each item the closest equivalent product on "
    "each app (same brand and pack size where possible) with price and "
    "per-unit price, marking anything out of stock; a small Markdown table "
    "works well. Then each app's total for the basket, which app is cheaper "
    "and by how much, and a one-line recommendation. Say that delivery fees "
    "aren't included. If an app lacks an item, say so.\n"
    "4. Ask which app to order from, unless the user already said (\"order "
    "from the cheaper one\"). Then add to that app's cart with its own tools, "
    "using the IDs and address id from the search, and follow that app's "
    "rules; placing the order asks the user for approval automatically.\n"
)


class GroceriesIntegration(Integration):
    name = "groceries"
    title = "Grocery price comparison"
    description = (
        "Compares prices across your grocery apps ("
        + ", ".join(p.title for p in PROVIDERS)
        + ") when you don't name one. Read-only; ordering uses the app you pick."
    )
    restricted = True                 # uses the owner's grocery accounts
    tool_labels = {
        "grocery_addresses": "Loading your delivery addresses",
        "search_groceries": "Searching grocery apps",
    }
    examples = ["Order milk and bread, wherever it's cheaper"]

    async def load_tools(self):
        # Runs after the apps' integrations (registry order), so their tools
        # are loaded. With one app, its own tools are simpler.
        return (GROCERY_TOOLS, None) if len(available_providers()) >= 2 else ([], None)

    def hides_tools(self):
        # One search for every app, so the address and comparison rules hold
        return set().union(*(p.search_tools for p in available_providers()))

    def rules(self, tool_names):
        return RULES

    def status(self, loaded_tool_names):
        if "search_groceries" in loaded_tool_names:
            return {"state": "connected", "detail": "Comparing " + ", ".join(p.title for p in available_providers()) + "."}
        return {"state": "disconnected", "detail": "Connect at least two grocery apps (Swiggy with Instamart, and Zepto)."}


INTEGRATION = GroceriesIntegration()
