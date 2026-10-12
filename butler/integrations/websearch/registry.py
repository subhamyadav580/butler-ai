"""Pick the web search provider (Strategy + Factory).

Adding a provider: create providers/<name>.py with a SearchProvider subclass,
then add it to PROVIDERS below. Nothing else changes.

Which providers are used, and in what order:
1. Only providers that have an API key (`is_configured()`).
2. Minus any the user switched off on the web UI's Integrations page.
3. The "use first" provider leads: the UI choice if made, else
   WEB_SEARCH_PROVIDER from .env, else the PROVIDERS order below.
The rest follow as fallbacks.

UI choices are stored in data/butler.db (settings table), so the web server
and the Telegram bot pick them up immediately, without a restart.
"""

from butler.db import get_settings

from .base import SearchProvider
from .config import WEB_SEARCH_PROVIDER
from .providers import FirecrawlProvider, SerperProvider, TavilyProvider

# Default order of preference
PROVIDERS: dict[str, type[SearchProvider]] = {
    "serper": SerperProvider,
    "tavily": TavilyProvider,
    "firecrawl": FirecrawlProvider,
}

SETTINGS_KEY = "web_search"


# ----------------------------------------------------------------------
# User preferences (from the UI)
# ----------------------------------------------------------------------

def load_preferences():
    """{"disabled": [names], "primary": name or None}. Stored as *disabled*
    so a newly added provider is on by default."""
    prefs = get_settings().get(SETTINGS_KEY, {}) or {}
    return {
        "disabled": [n for n in prefs.get("disabled", []) if n in PROVIDERS],
        "primary": prefs.get("primary") if prefs.get("primary") in PROVIDERS else None,
    }


def save_preferences(enabled, primary=None):
    """enabled: {name: bool} for any providers; primary: name or None."""
    unknown = [n for n in [*enabled, primary] if n and n not in PROVIDERS]
    if unknown:
        raise ValueError(f"Unknown web search provider(s): {', '.join(unknown)}")

    current = load_preferences()
    disabled = set(current["disabled"])
    for name, on in enabled.items():
        (disabled.discard if on else disabled.add)(name)

    get_settings().set(SETTINGS_KEY, {
        "disabled": sorted(disabled),
        "primary": primary if primary is not None else current["primary"],
    })


def _primary_name(prefs):
    if prefs["primary"]:
        return prefs["primary"]
    if WEB_SEARCH_PROVIDER and WEB_SEARCH_PROVIDER not in PROVIDERS:
        raise ValueError(
            f"Unknown WEB_SEARCH_PROVIDER '{WEB_SEARCH_PROVIDER}'. Choose from: {', '.join(PROVIDERS)}"
        )
    return WEB_SEARCH_PROVIDER or None


# ----------------------------------------------------------------------
# Lookups
# ----------------------------------------------------------------------

def get_providers():
    """Providers to try, in order: configured, switched on, "use first" leading."""
    prefs = load_preferences()
    primary = _primary_name(prefs)
    names = sorted(PROVIDERS, key=lambda n: n != primary)     # stable: primary first
    providers = [PROVIDERS[n]() for n in names if n not in prefs["disabled"]]
    return [p for p in providers if p.is_configured()]


def get_provider():
    """The provider tried first, or None if none is usable."""
    providers = get_providers()
    return providers[0] if providers else None


def any_configured():
    """True if at least one provider has an API key (even if switched off)."""
    return any(cls().is_configured() for cls in PROVIDERS.values())


def provider_overview():
    """Every known provider with its state, for the Integrations page."""
    prefs = load_preferences()
    active = [p.name for p in get_providers()]
    return [
        {
            "name": name,
            "title": cls.title or name,
            "key_setting": cls.key_setting,
            "configured": cls().is_configured(),
            "enabled": name not in prefs["disabled"],
            "primary": bool(active) and active[0] == name,
        }
        for name, cls in PROVIDERS.items()
    ]
