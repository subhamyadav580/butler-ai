# Swiggy

Butler connects to three Swiggy services through Swiggy's official [MCP servers](https://mcp.swiggy.com/builders/). They act on **your real Swiggy account**: your saved addresses, carts, orders and bookings.

| Service | What it does | Tools |
|---|---|---|
| 🍔 **Food** | Restaurant delivery: search dishes and restaurants, menus, cart, coupons, ordering, tracking | 19 |
| 🛒 **Instamart** | Groceries and essentials in minutes: product search, "my usual" items, cart, checkout, tracking | 15 |
| 🍽️ **Dineout** | Table reservations: find restaurants, check slots, book free tables, booking status | 10 |

India only. One login covers all three.

## What you can ask

```
Find veg biryani near my Office                       ← Food
Add 1 Classic Paneer Subz Biryani, King Size, to my cart
Place the order, cash on delivery                     ← asks you to Approve

Search Instamart for Amul Taaza milk                  ← Instamart
Add 1 pack of milk and any Britannia bread to my Instamart cart
Order my usual Instamart items
Place the Instamart order, cash on delivery           ← asks you to Approve

Find Italian restaurants in Connaught Place, Delhi    ← Dineout
Show tomorrow's dinner slots at the first one
Book a free table for 2 at 8 pm                       ← asks you to Approve
```

Butler chooses the service from what you ask for: a meal delivered means Food, groceries mean Instamart, and eating out means Dineout. Naming the service ("on Instamart") helps when it's ambiguous.

## Connect

No developer setup is needed. Just log in:

```bash
python -m butler swiggy-login
```

1. A browser opens on Swiggy's login page.
2. Enter your phone number and the OTP.
3. The terminal lists the tools for each enabled service, and your saved addresses.

The login is saved in `secrets/swiggy_token.json`. You can also click **Connect** next to Swiggy on the web UI's **Integrations** page.

> **The login expires after 5 days.** Swiggy's API doesn't support refreshing it yet. When Butler says *"Swiggy login has expired"*, run `python -m butler swiggy-login` again. The Integrations page shows how many days are left.

## Choosing services

All three load by default. To load fewer, set this in `.env`:

```
SWIGGY_SERVICES=food,instamart        # any of: food, instamart, dineout
```

Fewer services means fewer tools for the model to choose from, which makes smaller models more accurate.

## What needs your approval

Butler never changes your account without asking. These actions pause the chat and show **Approve / Reject**, with a preview:

| Action | Preview shown |
|---|---|
| Place or confirm a **Food** order | Your Food cart: items, total, taxes |
| Check out or confirm an **Instamart** order | Your Instamart cart |
| **Book a Dineout table**, or confirm a Dineout payment | Guests, date and time, free or paid, restaurant name, address and rating |
| Add or delete a saved address | The address details |
| Clear a cart (Food or Instamart) | — |

Searching, browsing menus and slots, viewing carts, adding items to a cart, applying coupons and tracking don't ask: they're read-only, or your request already is the confirmation, and nothing is charged.

If you reject, nothing changes. If you send a new message instead of answering, that counts as a reject.

## Good to know

**Food**
- Items with sizes or add-ons: say what you want ("King Size, no add-ons"), or Butler asks.
- Paying: cash on delivery is the simplest. UPI goes through Swiggy's app.

**Instamart**
- **Each cart update replaces the whole cart.** Butler re-sends your existing items every time, so they aren't lost.
- Some products have a per-order limit (for example "max 1"). Butler tells you.
- Not every address is served. If yours isn't, Butler says so; try another saved address.

**Dineout**
- **Free tables** book in one step after you approve.
- **Paid deals** (prebook offers with a price) need UPI payment in the Swiggy app. Butler shows the price and offers a free slot instead, or suggests booking the paid one in the app.
- **Cancelling isn't available** through Swiggy's API. Cancel in the Swiggy app.
- Name the area ("in Connaught Place") or say "near my Office" so Butler searches the right place.

**General**
- **Model choice matters.** Swiggy flows take several steps and pass long IDs between tools. `gpt-4.1-mini` handles them well. `gpt-4o-mini`, the default, sometimes invents IDs or keeps asking for confirmation. Set `OPENAI_MODEL=gpt-4.1-mini` if you use Swiggy a lot.
- **Rate limits:** Swiggy limits bursts of requests (`429`). Butler retries briefly at startup. If one service still fails, the others keep working, and the Integrations page says which service is missing; **Reload agent** retries.
- **Personal use is allowed without approval.** Swiggy lets you use the MCP servers for personal use on `localhost` without applying. If you build a product for other people on them, apply at [mcp.swiggy.com/builders/access](https://mcp.swiggy.com/builders/docs/operate/access/).
- **On Telegram, restrict who can order.** Set `TELEGRAM_OWNER_ID` so only you can use Swiggy. See the [Telegram guide](../interfaces/telegram.md).
- **Where the code lives:** [`butler/integrations/swiggy/`](../../butler/integrations/swiggy/). How it works: [Tools: MCP tools](../internals/tools.md#mcp-tools-swiggy).
