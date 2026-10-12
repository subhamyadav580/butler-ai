"""Tavily (https://tavily.com): search built for AI agents, with its own answer."""

import httpx

from ..config import TAVILY_API_KEY, TAVILY_SEARCH_DEPTH

from ..base import SearchError, SearchProvider, SearchResponse, SearchResult

ENDPOINT = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 30

# Tavily returns long page excerpts; keep each result LLM-sized
SNIPPET_CHARS = 500

# Tavily wants a full country name; Butler's settings use 2-letter codes
COUNTRY_NAMES = {
    "in": "india", "us": "united states", "gb": "united kingdom", "uk": "united kingdom",
    "ca": "canada", "au": "australia", "de": "germany", "fr": "france", "jp": "japan",
    "sg": "singapore", "ae": "united arab emirates", "nz": "new zealand", "ie": "ireland",
    "za": "south africa", "br": "brazil", "es": "spain", "it": "italy", "nl": "netherlands",
}


class TavilyProvider(SearchProvider):
    name = "tavily"
    title = "Tavily"
    key_setting = "TAVILY_API_KEY"

    def __init__(self, api_key: str = TAVILY_API_KEY, depth: str = TAVILY_SEARCH_DEPTH):
        self.api_key = api_key
        self.depth = depth if depth in ("basic", "advanced") else "basic"

    def is_configured(self):
        return bool(self.api_key)

    def search(self, query, *, search_type="web", num=8, country=None, time_range="any"):
        payload = {
            "query": query,
            "max_results": num,
            "search_depth": self.depth,          # basic = 1 credit, advanced = 2
            "include_answer": "basic",
            "topic": "news" if search_type == "news" else "general",
        }
        if time_range != "any":
            payload["time_range"] = time_range   # day | week | month | year
        # Tavily only boosts by country for general (non-news) searches
        if country and search_type == "web" and country.lower() in COUNTRY_NAMES:
            payload["country"] = COUNTRY_NAMES[country.lower()]

        try:
            response = httpx.post(
                ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise SearchError(f"Tavily request failed: {error}") from error

        if response.status_code == 401:
            raise SearchError("Tavily rejected the API key. Check TAVILY_API_KEY in .env.")
        if response.status_code in (429, 432, 433):
            raise SearchError("Tavily rate limit or plan limit reached. Try again later.")
        if response.status_code >= 400:
            raise SearchError(f"Tavily error {response.status_code}: {response.text[:200]}")

        data = response.json()
        results = [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=_snippet(item.get("content", "")),
                date=item.get("published_date"),
            )
            for item in data.get("results", [])[:num]
            if item.get("url")
        ]
        return SearchResponse(query=query, provider=self.name,
                              results=results, answer=data.get("answer") or None)


def _snippet(text):
    text = " ".join(text.split())
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1].rstrip() + "…"
