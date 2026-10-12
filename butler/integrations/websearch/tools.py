from typing import Optional

from langchain_core.tools import tool

from .config import WEB_SEARCH_COUNTRY

from .base import SearchError, SearchType, TimeRange
from .registry import any_configured, get_providers


@tool
def web_search(
    query: str,
    search_type: SearchType = "web",
    num_results: int = 8,
    time_range: TimeRange = "any",
    country: Optional[str] = None,
) -> dict:
    """Search the web for current or factual information.

    Use for anything that may have changed recently or that you don't know
    for sure: news, live scores, prices, weather, opening hours, release
    dates, people and companies, "latest…" questions.

    Args:
        query: A focused search query, like you'd type into Google
            ("india vs west indies score", "iphone 17 price india").
        search_type: "web" (default) or "news" for recent articles.
        num_results: How many results (1-10).
        time_range: "any" (default), "day", "week", "month" or "year": only
            results from that period. Use "day" for live scores and breaking news.
        country: 2-letter country code to localise results ("in", "us").
            Defaults to the user's configured country.
    """
    # Read on every search: provider switches on the Integrations page apply at once
    providers = get_providers()
    if not providers:
        return {"error": (
            "Web search is turned off: every provider is switched off on the "
            "Integrations page, or none has an API key in .env."
        )}

    errors = []
    for provider in providers:          # chosen provider first, the rest as fallback
        try:
            response = provider.search(
                query,
                search_type=search_type,
                num=max(1, min(num_results, 10)),
                country=(country or WEB_SEARCH_COUNTRY or None),
                time_range=time_range,
            )
            break
        except SearchError as error:
            errors.append(str(error))
    else:
        return {"error": " / ".join(errors)}

    result = response.to_dict()
    # Instructions next to the data are followed more reliably than prompt rules
    result["note"] = (
        "Answer only from these results, say how recent the information is, "
        "and cite 1-3 sources as markdown links [site](url)."
    )
    return result


def get_web_search_tools():
    """([web_search], [active provider names]) when any provider has a key, else ([], []).

    The tool stays available even if the user switched every provider off,
    so switching one back on works without restarting Butler.
    """
    if not any_configured():
        return [], []
    return [web_search], [p.name for p in get_providers()]
