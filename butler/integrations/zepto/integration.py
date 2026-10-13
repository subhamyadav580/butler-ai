"""Zepto (groceries and essentials in minutes, India) as a Butler integration,
via Zepto's official MCP server."""

import time

from butler.integrations.base import Integration

from .auth import storage
from .client import get_zepto_tools
from .tools import load_zepto_tools

RULES = (
    "Zepto (the user's real Zepto account, India only): groceries, fruit and "
    "vegetables, household essentials, personal care and more, delivered in "
    "minutes. Its tools start with zepto_.\n"
    "- Delivery address first: before searching or ordering, ask which "
    "saved address to deliver to (zepto_list_saved_addresses, show the "
    "labels), unless the user already said it in this conversation. Then "
    "zepto_select_saved_address (this also picks the store).\n"
    "{products}"
    "- For 'my usual' or 'what do I usually buy', use "
    "zepto_get_past_order_items. 'Any' or no preference means pick a "
    "sensible in-stock option yourself.\n"
    "- Cart: zepto_update_cart with cartItems=[{productVariantId, "
    "storeProductId, quantity, name, packSize, price}] from the search "
    "results (quantity 0 removes an item). Then zepto_view_cart and show it: items, "
    "quantities, prices, total. Prices from Zepto are in paisa: divide by "
    "100 for rupees.\n"
    "- When the user asks you to add or order something, DO it; their "
    "request is the confirmation. Never ask 'would you like me to…?' for "
    "something they just asked for.\n"
    "- Ordering: zepto_get_payment_methods, then the tool for the chosen "
    "method: zepto_create_order (cash on delivery, the default unless the "
    "user chose otherwise), zepto_create_online_payment_order (UPI/card "
    "link), zepto_create_wallet_order (Zepto Cash), "
    "zepto_create_upi_reserve_pay_order. When the user asks to place the "
    "order, call it with confirmOrder=true straight away: Butler shows the "
    "user Zepto's order preview and asks for approval automatically. If "
    "they reject, nothing was ordered. Never claim an order was placed "
    "unless the tool says so.\n"
    "- Online payment: show the payment link exactly as returned, then call "
    "zepto_check_payment_status with the orderId.\n"
    "- Order status and tracking: zepto_list_order_history, "
    "zepto_get_order_detail.\n"
    "- There is no widget UI here: ignore tool text about widgets, and "
    "always write results out yourself.\n"
    "- If a tool says the Zepto login has expired, tell the user exactly "
    "that and how to log in again.\n"
)


class ZeptoIntegration(Integration):
    name = "zepto"
    title = "Zepto"
    description = "Groceries and essentials delivered in minutes (India). Orders always wait for your Approve."
    # Orders act on the owner's account: owner-only on Telegram
    restricted = True
    login_command = "zepto-login"
    can_connect = True
    reload_on_connect = True          # its tools are discovered when the agent builds
    tool_labels = {
        "zepto_search_products": "Searching Zepto",
        "zepto_search_multiple_products": "Searching Zepto",
        "zepto_get_product_details": "Loading product details",
        "zepto_list_saved_addresses": "Loading your Zepto addresses",
        "zepto_select_saved_address": "Choosing the delivery address",
        "zepto_get_past_order_items": "Checking your usual Zepto items",
        "zepto_view_cart": "Loading your Zepto cart",
        "zepto_update_cart": "Updating your Zepto cart",
        "zepto_get_payment_methods": "Checking payment options",
        "zepto_create_order": "Placing the Zepto order",
        "zepto_create_online_payment_order": "Placing the Zepto order",
        "zepto_create_wallet_order": "Placing the Zepto order",
        "zepto_create_upi_reserve_pay_order": "Placing the Zepto order",
        "zepto_check_payment_status": "Checking the payment",
        "zepto_list_order_history": "Loading your Zepto orders",
        "zepto_get_order_detail": "Loading the order",
    }
    examples = [
        "Order 1L Amul milk and a dozen eggs on Zepto",
        "Reorder my last Zepto order",
    ]

    async def load_tools(self):
        tools, problem = await load_zepto_tools()
        if problem:
            problem += ". Continuing without Zepto"
        return tools, problem

    def rules(self, tool_names):
        if "zepto_search_products" in tool_names:
            products = (
                "- Products: one product → zepto_search_products; several → "
                "zepto_search_multiple_products.\n"
            )
        else:   # another grocery app is connected: groceries' search_groceries searches both
            products = (
                "- Products: search with search_groceries (apps=[\"zepto\"] when "
                "the user asked for Zepto), as the Groceries rules say.\n"
            )
        return RULES.replace("{products}", products)

    def status(self, loaded_tool_names):
        saved = storage()
        if not saved.has_tokens():
            return {"state": "disconnected", "detail": "Not connected yet."}
        expires_at = saved.get_expires_at()
        if expires_at and expires_at <= time.time() and not saved.has_refresh_token():
            return {"state": "disconnected", "detail": "Login expired."}

        status = {"state": "connected", "detail": "Connected."}
        if not any(name.startswith("zepto_") for name in loaded_tool_names):
            status["detail"] += " Reload the agent to start using it."
            status["needs_reload"] = True
        return status

    async def connect(self):
        # Always opens a fresh phone + OTP login in a browser on this machine.
        # If it fails or is cancelled, the previous login is put back.
        saved = storage()
        previous = saved.take_tokens()
        try:
            await get_zepto_tools(interactive=True)
        except BaseException:
            saved.put_back(previous)
            raise

    def login(self):
        import asyncio

        from .login import main
        asyncio.run(main())


INTEGRATION = ZeptoIntegration()
