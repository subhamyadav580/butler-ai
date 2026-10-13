"""Zepto, through the Zepto integration's loaded MCP tools."""

from butler.integrations.zepto.tools import RAW_TOOLS

from ..base import Address, GroceryError, GroceryProvider, Offer, structured

MAX_OFFERS = 8


class ZeptoProvider(GroceryProvider):
    name = "zepto"
    title = "Zepto"
    search_tools = {"zepto_search_products", "zepto_search_multiple_products"}
    order_hint = (
        "zepto_select_saved_address(<address id>), zepto_update_cart(cartItems=[{"
        "productVariantId, storeProductId, quantity, name, packSize, price}]), then "
        "the order tool for the payment method"
    )

    def available(self):
        return {"zepto_list_saved_addresses", "zepto_select_saved_address", "zepto_search_products"} <= set(RAW_TOOLS)

    async def addresses(self):
        data = await structured(RAW_TOOLS["zepto_list_saved_addresses"], {})
        return [
            Address(app=self.name, id=a["id"], label=a.get("label", ""), text=a.get("addressLine", ""),
                    postal_code=a.get("postalCode"))
            for a in data.get("addresses", [])
        ]

    async def prepare(self, address):
        # Zepto searches the store of the selected address
        await RAW_TOOLS["zepto_select_saved_address"].ainvoke({"addressId": address.id})

    async def search(self, query, address):
        data = await structured(RAW_TOOLS["zepto_search_products"], {"query": query})
        if "products" not in data:
            raise GroceryError(data.get("message") or "no results")
        return [
            Offer(
                app=self.name, name=p.get("name", ""), pack=p.get("packSize", ""),
                price=(p.get("price") or 0) / 100,                       # paisa → ₹
                mrp=(p["mrp"] / 100) if p.get("mrp") else None,
                in_stock=(p.get("availableQuantity") or 0) > 0,
                ids={"productVariantId": p.get("productVariantId"), "storeProductId": p.get("storeProductId")},
            )
            for p in data["products"][:MAX_OFFERS]
        ]
