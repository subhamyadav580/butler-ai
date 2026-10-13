"""Matching addresses across apps, and comparable unit prices."""

import re

STOPWORDS = {"india", "floor", "the", "and", "near", "opp", "no", "road", "rd", "block", "sector", "phase"}


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOPWORDS}


def score(query, address):
    """How well what the user said ("RK", "office", "sector 28") picks this address."""
    q = (query or "").strip().lower()
    if not q:
        return 0
    if q == address.label.strip().lower():
        return 100
    words = tokens(q)
    if not words:
        return 0
    found = words & tokens(f"{address.label} {address.text}")
    return 60 * len(found) / len(words) + (30 if address.postal_code and address.postal_code in q else 0)


def similarity(a, b):
    """How likely two addresses from different apps are the same place."""
    ta, tb = tokens(f"{a.label} {a.text}"), tokens(f"{b.label} {b.text}")
    overlap = len(ta & tb) / max(1, min(len(ta), len(tb)))
    same_label = a.label.strip().lower() == b.label.strip().lower()
    same_pin = bool(a.postal_code and a.postal_code == b.postal_code) or bool(
        set(re.findall(r"\b\d{6}\b", a.text)) & set(re.findall(r"\b\d{6}\b", b.text)))
    return overlap + (0.5 if same_label else 0) + (0.3 if same_pin else 0)


def pick(addresses, query):
    """The address the user meant, or None."""
    best = max(addresses, key=lambda a: score(query, a), default=None)
    return best if best and score(query, best) >= 30 else None


def closest(addresses, other):
    """The address in this app most like `other` (from another app), or None."""
    best = max(addresses, key=lambda a: similarity(a, other), default=None)
    return best if best and similarity(best, other) >= 0.5 else None


# --- Unit prices ------------------------------------------------------------

UNITS = {"ml": ("ml", 1), "l": ("ml", 1000), "ltr": ("ml", 1000), "litre": ("ml", 1000),
         "g": ("g", 1), "gm": ("g", 1), "gms": ("g", 1), "kg": ("g", 1000),
         "pc": ("pc", 1), "pcs": ("pc", 1), "piece": ("pc", 1), "pieces": ("pc", 1)}


def quantity(pack):
    """(amount, base unit) from "500 ml x 4", "1 pack (1 L)", "6 pcs"; None if unknown."""
    text = (pack or "").lower()
    found = re.findall(r"(\d+(?:\.\d+)?)\s*(ml|ltr|litre|l|kg|gms|gm|g|pcs|pc|pieces|piece)\b", text)
    if not found:
        return None
    amount, unit = found[-1]               # "1 pack (1 L)": the size in brackets
    base, factor = UNITS[unit]
    times = re.search(r"x\s*(\d+)|(\d+)\s*x\b", text)
    count = int(next(g for g in times.groups() if g)) if times else 1
    return float(amount) * factor * count, base


def unit_price(price, pack):
    """"₹6.0/100 ml" style string for comparing pack sizes, or None."""
    q = quantity(pack)
    if not q or not q[0]:
        return None
    amount, base = q
    if base == "pc":
        return f"₹{price / amount:.1f}/pc"
    return f"₹{price * 100 / amount:.1f}/100 {base}"
