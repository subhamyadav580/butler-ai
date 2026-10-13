# Zepto

Butler connects to Zepto through Zepto's official [MCP server](https://github.com/zeptonow/mcp) (`https://mcp.zepto.co.in/mcp`). It acts on **your real Zepto account**: your addresses, cart and orders. Orders are real and are delivered like any order from the Zepto app.

India only. You need a Zepto account with an Indian mobile number.

## What you can ask

```
Use my Work address on Zepto and search for Amul Taaza milk
Add 1L Amul milk, a dozen eggs and any brown bread to my Zepto cart
Show my Zepto cart
Place the order, cash on delivery          ← asks you to Approve
Reorder my last Zepto order
What did I order on Zepto last week?
I'm making paneer butter masala for 4, order what I need from Zepto
```

Butler first checks your **usual items** (your last 30+ orders), so "milk" finds the brand you normally buy. Prices come back in paisa and are shown in rupees.

**Address first.** Before searching or ordering, Butler asks which saved address to deliver to, unless you've already said it ("…deliver to RK").

**Zepto and Instamart both connected?** If you don't name an app, Butler searches both and compares prices; see [Grocery comparison](groceries.md). Say "on Zepto" to use only Zepto.

## Connect

No developer setup is needed. Just log in:

```bash
python -m butler zepto-login
```

1. A browser opens on Zepto's login page.
2. Enter your phone number and the OTP.
3. The terminal lists Zepto's tools and marks the ones that will ask for your approval.

The login is saved in `secrets/zepto_token.json`. You can also click **Connect** next to Zepto on the web UI's **Integrations** page, then **Reload agent**.

Zepto issues a **refresh token**, so unlike Swiggy the login doesn't need redoing every few days. If Butler ever says *"Zepto login has expired"*, run `python -m butler zepto-login` again.

## What needs your approval

Butler never places an order or changes your account without asking. These pause the chat and show **Approve / Reject**:

| Action | Preview shown |
|---|---|
| **Place an order**: cash on delivery, online payment link (UPI/card), Zepto Cash, or UPI Reserve Pay | Zepto's own order preview: items, total, address |
| Add a saved address | The address details |
| Change your name on Zepto | The new name |

Zepto's order tools work in two steps: `confirmOrder=false` returns a preview and orders nothing, and `confirmOrder=true` places the order. Only the second step asks for approval, and the card shows the preview.

These run without asking, because nothing is charged: searching, your usual items, viewing and editing the cart, choosing the delivery address, payment options, order history and payment status.

A tool Zepto adds later asks first, unless its name says it only reads (`get_…`, `list_…`, `search_…`). `python -m butler zepto-login` prints which tools ask.

If you reject, nothing changes. If you send a new message instead of answering, that counts as a reject.

## Paying

- **Cash on delivery** is the simplest, and Butler prefers it unless you choose otherwise.
- **UPI or card:** Zepto returns a payment link; Butler shows it, and you pay in the browser or your UPI app.
- **Zepto Cash** (wallet) also works if you have a balance.

## Good to know

- **On Telegram,** Zepto, like Swiggy, is only for `TELEGRAM_OWNER_ID` when that's set, and only they can approve an order.
- **Disconnecting:** delete `secrets/zepto_token.json`.
- **Where the code lives:** [`butler/integrations/zepto/`](../../butler/integrations/zepto/). The login is shared with Swiggy in [`mcp_oauth.py`](../../butler/integrations/mcp_oauth.py); `tools.py` holds the approval rules.
