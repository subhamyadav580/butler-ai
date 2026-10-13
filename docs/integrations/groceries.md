# Groceries: compare Instamart and Zepto

When both **Swiggy Instamart** and **Zepto** are connected, Butler searches both for your groceries and shows the prices side by side, so you can order from the cheaper one.

There's nothing to set up: it turns on by itself once [Swiggy](swiggy.md) (with Instamart) and [Zepto](zepto.md) are both connected. With only one of them connected, Butler just uses that app.

## How it works

```
You:    Order 1 litre milk and brown bread
Butler: Which address should I deliver to?  RK · Office · work · home · …
You:    RK
Butler: | Item        | Swiggy Instamart                      | Zepto                                  |
        |-------------|---------------------------------------|----------------------------------------|
        | Milk 1 L    | Amul Taaza Milk 1 Ltr - ₹59           | Amul Pasteurised Cow Fresh Milk - ₹61  |
        | Brown bread | Harvest Gold Hearty Brown 400 g - ₹60 | Harvest Gold Hearty Brown 400 g - ₹60  |
        | Total       | ₹119                                  | ₹121                                   |
        Instamart is ₹2 cheaper (delivery fees not included). Which app should I order from?
You:    Instamart
Butler: (adds to your Instamart cart, shows it, and asks you to Approve the order)
```

1. **Address first.** For any grocery search or order, Butler asks which saved address to deliver to, unless you've already said it in this conversation ("…deliver to RK"). It never picks one for you.
2. **One search, both apps.** Butler searches both apps for every item at that address. The same address can have different labels in each app; Butler matches them by label and by the address itself (area, PIN code).
3. **Side by side.** For each item it picks the same brand and pack size on both apps where possible, shows the price and per-unit price (₹/100 ml, ₹/100 g, ₹/piece), and totals the basket.
4. **You choose the app,** then Butler orders there as usual: the order still needs your **Approve**.

**Naming an app skips the comparison:** "search **Zepto** for eggs" or "order milk **on Instamart**" uses only that app (after asking for the address).

## Good to know

- **Prices exclude delivery and handling fees.** Each app adds those at checkout, and the approval card shows the final amount.
- **The search is read-only.** Nothing is added to a cart until you choose an app.
- **Rate limits.** The apps limit bursts of requests; Butler searches one item at a time per app and retries briefly. A long list takes a few seconds.
- **On Telegram,** like Swiggy and Zepto, it's only for `TELEGRAM_OWNER_ID` when that's set.

## How it's built

[`butler/integrations/groceries/`](../../butler/integrations/groceries/) is its own integration with one provider per app:

| File | Does |
|---|---|
| `base.py` | App-neutral `Address` and `Offer` types and the `GroceryProvider` contract |
| `providers/instamart.py`, `providers/zepto.py` | Each app's addresses and search, from its MCP tools' structured results |
| `registry.py` | The list of providers |
| `matching.py` | Matching addresses across apps; per-unit prices from pack sizes |
| `service.py` | Runs the search across apps and writes the side-by-side result |
| `tools.py` | `grocery_addresses` and `search_groceries` for the agent |

While it's active, each app's own product-search tools are hidden from the model (`hides_tools()`), so every grocery search goes through `search_groceries` and the address and comparison rules always apply. Carts and orders still use each app's own tools.

**Adding a grocery app** (say Blinkit, once it has an MCP server): add its integration, then a provider in `providers/` with `addresses()`, `search()` and its `search_tools`, and one line in `registry.py`.
