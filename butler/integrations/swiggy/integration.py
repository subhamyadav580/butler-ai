"""Swiggy (Food, Instamart, Dineout) as a Butler integration, via Swiggy's MCP servers."""

import os
import time

from butler.integrations.base import Integration

from .auth import FileTokenStorage
from .client import get_swiggy_tools
from .config import SERVERS
from .tools import load_swiggy_tools, smoke_test

COMMON_RULES = (
    "Swiggy (the user's real Swiggy account, India only). Tool names start "
    "with the service: food_* = restaurant food delivery, instamart_* = "
    "groceries and household essentials delivered in minutes, dineout_* = "
    "booking a table to eat out. Pick the service from what the user wants "
    "(a meal delivered → food; milk, snacks, groceries, household items → "
    "instamart; going out, booking a table → dineout) and use only that "
    "service's tools for the whole flow.\n"
    "- There is NO widget, picker or button UI here: ignore tool text about "
    "widgets, tapping, or 'Proceed to payment'. The user replies in chat. "
    "Always write results out yourself (items, quantities, prices, totals, "
    "address, times).\n"
    "- Addresses: if the user named one (a label like 'Home' or 'Office', or "
    "an area), that IS their choice; use its ID without asking again. This "
    "overrides tool text that says to confirm the address. Only ask when "
    "no saved address matches.\n"
    "- 'Any' or no preference means pick a sensible in-stock option yourself "
    "(the first good match) instead of asking. Ask only when a required "
    "choice is genuinely missing (size of a dish, number of guests).\n"
    "- When the user asks you to do something (add to cart, order, book), DO "
    "it; their request is the confirmation. Never ask 'would you like me "
    "to…?' for something they just asked for.\n"
    "- Orders, bookings, address changes and clearing a cart ask the user "
    "for approval automatically, so just call the tool. If they reject, "
    "nothing happened. Never claim an order or booking succeeded unless the "
    "tool says so.\n"
    "- Payment: for deliveries prefer Cash on Delivery "
    "(paymentMethod=\"Cash\"), and say so before ordering. UPI app payments "
    "need the Swiggy app; suggest finishing those there.\n"
    "- If a tool says the Swiggy login has expired, tell the user exactly "
    "that and how to log in again.\n"
)

FOOD_RULES = (
    "Swiggy Food (food_*):\n"
    "- Steps to add an item: (1) food_search_menu with the addressId to get "
    "the item's menu item ID and restaurantId; (2) if the item has variants "
    "or add-ons and the user didn't specify, call food_search_menu again "
    "with restaurantIdOfAddedItem to see the options, and ask only if a "
    "required choice is missing; (3) food_update_food_cart with addressId, "
    "restaurantId and cartItems=[{menu_item_id, quantity, variants or "
    "variantsV2 if chosen}]. addressId is required even though it isn't in "
    "the schema. (4) food_get_food_cart, and show it.\n"
    "- Order with food_place_food_order(addressId, paymentMethod).\n"
)

INSTAMART_RULES = (
    "Swiggy Instamart (instamart_*), groceries:\n"
    "- (1) instamart_get_addresses → addressId. (2) instamart_search_products"
    "(addressId, query). Results have variants (pack sizes, brands): pick "
    "the one matching what the user asked for, and ask only if it's "
    "genuinely ambiguous. For 'my usual' or reorders, use "
    "instamart_your_go_to_items.\n"
    "- instamart_update_cart REPLACES THE WHOLE CART. Before every update, "
    "call instamart_get_cart and send ALL items to keep plus the new ones, "
    "each with skuId, spinId and quantity, along with selectedAddressId. "
    "Otherwise existing items are dropped.\n"
    "- Show the cart from instamart_get_cart (items, quantities, prices, "
    "total). Order with instamart_checkout(addressId, paymentMethod=\"Cash\" "
    "unless the user chose otherwise).\n"
    "- Tracking: instamart_get_orders to find the order, then "
    "instamart_track_order.\n"
)

DINEOUT_RULES = (
    "Swiggy Dineout (dineout_*), table reservations, not delivery:\n"
    "- Location: 'near home/office/me' → dineout_get_saved_locations, then "
    "pass addressId. A named city or area → pass its latitude and "
    "longitude.\n"
    "- dineout_search_restaurants_dineout takes ONE search term (a "
    "restaurant name, cuisine, area or vibe), not the user's sentence.\n"
    "- Availability: dineout_get_available_slots(restaurantId, date as "
    "YYYY-MM-DD, latitude, longitude) returns 7 days of slots. Each slot "
    "has deals: FREE (isFree=true) or PAID prebook deals (with a price). "
    "Use the restaurant's coordinates from the search results if you "
    "don't have the user's.\n"
    "- Book FREE deals with dineout_book_table(restaurantId, slotId, itemId, "
    "reservationTime, guestCount, latitude, longitude). Ask for the number "
    "of guests if you don't know it. PAID deals need UPI in the Swiggy app: "
    "tell the user the price and offer a free deal instead, or suggest "
    "booking the paid one in the Swiggy app.\n"
    "- Bookings can't be cancelled from here; tell the user to cancel in the "
    "Swiggy app. dineout_get_booking_status shows a booking.\n"
)

SERVICE_RULES = {"food": FOOD_RULES, "instamart": INSTAMART_RULES, "dineout": DINEOUT_RULES}


class SwiggyIntegration(Integration):
    name = "swiggy"
    title = "Swiggy"
    description = (
        "Food delivery, Instamart groceries and Dineout table bookings (India). "
        "Enabled: " + ", ".join(SERVERS) + "."
    )
    # Orders and bookings act on the owner's account: owner-only on Telegram
    restricted = True
    login_command = "swiggy-login"
    can_connect = True
    reload_on_connect = True          # its tools are discovered when the agent builds
    tool_labels = {
        "food_get_addresses": "Loading your Swiggy addresses",
        "food_search_restaurants": "Searching restaurants",
        "food_search_menu": "Searching dishes",
        "food_get_restaurant_menu": "Loading the menu",
        "food_update_food_cart": "Updating your cart",
        "food_get_food_cart": "Loading your cart",
        "food_place_food_order": "Placing the order",
        "food_track_food_order": "Tracking your order",
        "instamart_get_addresses": "Loading your Swiggy addresses",
        "instamart_search_products": "Searching Instamart",
        "instamart_your_go_to_items": "Loading your usual items",
        "instamart_get_cart": "Loading your Instamart cart",
        "instamart_update_cart": "Updating your Instamart cart",
        "instamart_checkout": "Placing the Instamart order",
        "instamart_track_order": "Tracking your order",
        "dineout_get_saved_locations": "Loading your locations",
        "dineout_search_restaurants_dineout": "Finding restaurants",
        "dineout_get_restaurant_details": "Loading restaurant details",
        "dineout_get_available_slots": "Checking available tables",
        "dineout_book_table": "Booking your table",
        "dineout_get_booking_status": "Checking your booking",
    }
    examples = [
        "Find veg biryani near my office on Swiggy",
        "Order milk and bread on Instamart",
        "Book a table for 2 tonight in Connaught Place",
    ]

    async def load_tools(self):
        tools, problem = await load_swiggy_tools()
        if problem and not tools:
            problem += ". Continuing without Swiggy"
        return tools, problem

    def rules(self, tool_names):
        services = services_of_names(tool_names)
        return COMMON_RULES + "".join(
            "\n" + SERVICE_RULES[s] for s in ("food", "instamart", "dineout") if s in services
        )

    def status(self, loaded_tool_names):
        storage = FileTokenStorage()
        expires_at = storage.get_expires_at() if os.path.exists(storage.path) else None
        if not expires_at or expires_at <= time.time():
            detail = "Login expired." if expires_at else "Not connected yet."
            return {"state": "disconnected", "detail": detail}

        loaded = services_of_names(loaded_tool_names)
        days_left = (expires_at - time.time()) / 86400
        detail = f"Connected. Login expires in {days_left:.1f} days (Swiggy limit)."
        status = {"state": "connected", "detail": detail, "expires_at": expires_at}
        missing = set(SERVERS) - loaded
        if not loaded:
            status["detail"] += " Reload the agent to start using it."
            status["needs_reload"] = True
        elif missing:
            status["detail"] += (
                f" Not loaded right now: {', '.join(sorted(missing))} "
                "(Swiggy may be rate-limiting). Reload the agent to retry."
            )
            status["needs_reload"] = True
        return status

    async def connect(self):
        # Opens a browser on this machine for phone + OTP, saves the token
        tools = await get_swiggy_tools(interactive=True)
        await smoke_test(tools)

    def login(self):
        import asyncio

        from .login import main
        asyncio.run(main())


def services_of_names(tool_names):
    """{"food", "instamart", …} from prefixed tool names."""
    return {name.split("_", 1)[0] for name in tool_names} & set(SERVICE_RULES)


INTEGRATION = SwiggyIntegration()
