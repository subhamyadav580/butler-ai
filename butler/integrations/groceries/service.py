"""Compare grocery prices across every connected app (Instamart, Zepto, …).

Framework-free: takes plain values, returns plain text for the agent.
"""

import asyncio

from butler.integrations.mcp_oauth import describe_error

from .matching import closest, pick, unit_price
from .registry import available_providers

OFFERS_PER_APP = 8
# Apps rate-limit bursts (HTTP 429 / "too many requests"): wait and retry
RETRY_DELAYS = (2, 5)
PAUSE_BETWEEN_ITEMS = 0.6


async def _addresses(providers):
    results = await asyncio.gather(*(p.addresses() for p in providers), return_exceptions=True)
    return dict(zip(providers, results, strict=True))


async def list_addresses():
    """Saved addresses in each app, so the user can choose one."""
    lines = []
    for provider, found in (await _addresses(available_providers())).items():
        if isinstance(found, BaseException):
            lines.append(f"{provider.title}: couldn't load addresses ({describe_error(found)})")
            continue
        lines.append(f"{provider.title}:")
        lines += [f"- [{a.label or 'no label'}] {a.text}" for a in found]
    return "\n".join(lines)


def _choose(addresses_by_app, wanted):
    """The address the user meant, in every app. Apps where it can't be found
    by what the user said get the address most like the one found elsewhere."""
    chosen = {}
    for provider, found in addresses_by_app.items():
        if not isinstance(found, BaseException):
            chosen[provider] = pick(found, wanted)
    anchor = next((a for a in chosen.values() if a), None)
    if anchor:
        for provider, address in chosen.items():
            if address is None:
                chosen[provider] = closest(addresses_by_app[provider], anchor)
    return chosen


async def _search_app(provider, address, items):
    await provider.prepare(address)
    results = {}
    for i, item in enumerate(items):       # one at a time: apps rate-limit bursts
        if i:
            await asyncio.sleep(PAUSE_BETWEEN_ITEMS)
        try:
            results[item] = await _with_retry(provider.search, item, address)
        except Exception as error:  # noqa: BLE001 — one failed item mustn't hide the rest
            results[item] = describe_error(error)
    return results


def _rate_limited(error):
    text = describe_error(error).lower()
    return "429" in text or "too many" in text or "rate limit" in text


async def _with_retry(search, item, address):
    for delay in (*RETRY_DELAYS, None):
        try:
            return await search(item, address)
        except Exception as error:
            if delay is None or not _rate_limited(error):
                raise
            await asyncio.sleep(delay)


async def search(items, address, apps=None):
    """Search the apps (all connected ones by default) for the items at the
    user's delivery address; returns a side-by-side text for the agent."""
    providers = available_providers()
    if apps:
        wanted = {a.lower() for a in apps}
        providers = [p for p in providers if p.name in wanted or p.title.lower() in wanted]
        if not providers:
            return f"No connected grocery app matches {apps}. Connected: " + ", ".join(
                p.name for p in available_providers())

    addresses_by_app = await _addresses(providers)
    chosen = _choose(addresses_by_app, address)
    if not any(chosen.values()):
        return (
            f"No saved address matches \"{address}\". Nothing was searched. Ask the "
            "user which address to deliver to, from these:\n" + await list_addresses()
        )

    lines, searches = ["Delivery address used:"], {}
    for provider in providers:
        found = addresses_by_app[provider]
        target = chosen.get(provider)
        if isinstance(found, BaseException):
            lines.append(f"- {provider.title}: unavailable ({describe_error(found)})")
        elif target is None:
            lines.append(f"- {provider.title}: no saved address matches \"{address}\"; skipped")
        else:
            lines.append(f"- {provider.title}: [{target.label}] {target.text} (address id {target.id})")
            searches[provider] = target

    results = await asyncio.gather(
        *(_search_app(p, a, items) for p, a in searches.items()), return_exceptions=True)
    by_app = dict(zip(searches, results, strict=True))

    for item in items:
        lines.append(f"\n## {item}")
        for provider, found in by_app.items():
            offers = found if isinstance(found, BaseException) else found.get(item)
            lines.append(f"{provider.title}:")
            if isinstance(offers, BaseException):
                lines.append(f"  unavailable ({describe_error(offers)})")
            elif isinstance(offers, str):
                lines.append(f"  search failed ({offers})")
            elif not offers:
                lines.append("  nothing found")
            else:
                offers = sorted(offers, key=lambda o: not o.in_stock)[:OFFERS_PER_APP]
                for o in offers:
                    per_unit = unit_price(o.price, o.pack)
                    mrp = f", MRP ₹{o.mrp:g}" if o.mrp and o.mrp > o.price else ""
                    stock = "" if o.in_stock else " — OUT OF STOCK"
                    ids = ", ".join(f"{k}={v}" for k, v in o.ids.items() if v)
                    lines.append(
                        f"  - {o.name} | {o.pack} | ₹{o.price:g}{mrp}"
                        + (f" ({per_unit})" if per_unit else "") + f"{stock} [{ids}]"
                    )

    lines.append("\nPrices exclude delivery and handling fees, which each app adds at checkout.")
    if len(searches) > 1:
        lines.append(
            "\nNEXT (for you, not the user): don't search these items again. Reply with a "
            "Markdown table: one row per item, one column per app, each cell the best "
            "match on that app (same brand and pack size on every app where possible; "
            "otherwise the closest, and say so) with its price. Add a Total row, then "
            "say which app is cheaper and by how much, note that delivery fees aren't "
            "included, and ask which app to order from."
        )
    lines.append("To order: " + " | ".join(f"{p.title}: {p.order_hint}" for p in searches))
    return "\n".join(lines)
