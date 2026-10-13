"""Swiggy Instamart, through the Swiggy integration's loaded MCP tools."""

from butler.integrations.swiggy.tools import RAW_TOOLS

from ..base import Address, GroceryError, GroceryProvider, Offer, structured

MAX_PRODUCTS = 8          # matching products per search
VARIANTS_PER_PRODUCT = 2  # single packs first: multipacks (500 ml x 12) crowd out other products


class InstamartProvider(GroceryProvider):
    name = "instamart"
    title = "Swiggy Instamart"
    search_tools = {"instamart_search_products"}
    order_hint = (
        "instamart_update_cart(selectedAddressId=<address id>, items=[{spinId, skuId, "
        "quantity}]) (send ALL items to keep, it replaces the cart), then "
        "instamart_checkout"
    )

    def available(self):
        return {"instamart_get_addresses", "instamart_search_products"} <= set(RAW_TOOLS)

    async def addresses(self):
        found, page = [], 1
        while page <= 3:
            data = await structured(RAW_TOOLS["instamart_get_addresses"], {"page": page})
            for a in data.get("addresses", []):
                line = a.get("addressLine", "")
                found.append(Address(
                    app=self.name, id=a["id"], label=a.get("addressTag") or a.get("addressCategory") or "",
                    text=line.split(": ", 1)[-1],          # drop the "Name: " prefix
                ))
            if not data.get("pagination", {}).get("hasMore"):
                break
            page += 1
        return found

    async def search(self, query, address):
        data = await structured(RAW_TOOLS["instamart_search_products"], {"addressId": address.id, "query": query})
        if "products" not in data:
            raise GroceryError(data.get("message") or "no results")
        offers = []
        for product in data["products"][:MAX_PRODUCTS]:
            variations = sorted(product.get("variations", []), key=lambda v: " x " in v.get("quantityDescription", ""))
            for v in variations[:VARIANTS_PER_PRODUCT]:
                price = v.get("price", {})
                offers.append(Offer(
                    app=self.name,
                    name=v.get("displayName") or product.get("displayName", ""),
                    pack=v.get("quantityDescription", ""),
                    price=float(price.get("offerPrice") or price.get("mrp") or 0),
                    mrp=price.get("mrp"),
                    in_stock=bool(v.get("isInStockAndAvailable")),
                    ids={"spinId": v.get("spinId"), "skuId": v.get("skuId")},
                ))
        return offers
