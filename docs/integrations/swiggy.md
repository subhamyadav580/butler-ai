# Swiggy

Butler connects to **Swiggy Food** through Swiggy's official [MCP server](https://mcp.swiggy.com/builders/). It acts on **your real Swiggy account**: your saved addresses, your cart, your orders.

## What you can ask

```
Which addresses do I have saved on Swiggy?
Find veg biryani near my Office
Show me the menu of Behrouz Biryani
Add 1 Classic Paneer Subz Biryani, King Size, to my cart
Any coupons for my cart?
Place the order, cash on delivery          ← asks you to Approve
Where is my order?
```

## Connect

No developer setup is needed. Just log in:

```bash
python -m butler swiggy-login
```

1. A browser opens on Swiggy's login page.
2. Enter your phone number and the OTP.
3. The terminal lists Swiggy's 20 tools and your saved addresses.

The login is saved in `secrets/swiggy_token.json`. You can also click **Connect** next to Swiggy on the web UI's **Integrations** page.

> **The login expires after 5 days.** Swiggy's API doesn't support refreshing it yet. When Butler says *"Swiggy login has expired"*, run `python -m butler swiggy-login` again. The web UI's Integrations page shows how many days are left.

## What needs your approval

Butler never changes your account without asking. These actions pause the chat and show **Approve / Reject**, along with the cart for orders:

| Action | Asks first? |
|---|---|
| Place or confirm an order | ✅ Always |
| Add or delete a saved address | ✅ Always |
| Clear the cart | ✅ Always |
| Add items to the cart, apply a coupon | No: your request is the confirmation, and nothing is charged |
| Search, menus, view cart, track orders | No: read-only |

If you reject, nothing is changed. If you send a new message instead of answering, that counts as a reject.

## Good to know

- **Availability:** India only, and Swiggy Food only for now. Instamart, Dineout and Scenes exist on the same MCP server and could be added later.
- **Paying:** cash on delivery is the simplest. UPI works through Swiggy's payment flow.
- **Personal use is allowed without approval.** Swiggy lets you use the MCP server for personal use on `localhost` without applying. If you build a product for other people on it, apply for production access at [mcp.swiggy.com/builders/access](https://mcp.swiggy.com/builders/docs/operate/access/).
- **Rate limits:** Swiggy limits requests. If many requests fail in a row with `429`, wait a minute.
- **On Telegram, restrict who can order.** Set `TELEGRAM_OWNER_ID` so only you can use Swiggy. See the [Telegram guide](../interfaces/telegram.md).
- **Where the code lives:** [`butler/integrations/swiggy/`](../../butler/integrations/swiggy/)
