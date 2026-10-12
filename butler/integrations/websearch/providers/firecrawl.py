"""Firecrawl (https://firecrawl.dev): web and news search (v2 /search).

Only search results are used: no page scraping (`scrapeOptions`), which
would cost extra credits for full-page content Butler doesn't need.
Firecrawl's "alexandria" source (an index of software tools, not web pages)
isn't used for web search.
"""

import re

import httpx

from ..config import FIRECRAWL_API_KEY

from ..base import SearchError, SearchProvider, SearchResponse, SearchResult

ENDPOINT = "https://api.firecrawl.dev/v2/search"
TIMEOUT_SECONDS = 30
SNIPPET_CHARS = 500

# Google-style time filter, which Firecrawl accepts as `tbs`
TIME_RANGES = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}


class FirecrawlProvider(SearchProvider):
    name = "firecrawl"
    title = "Firecrawl"
    key_setting = "FIRECRAWL_API_KEY"

    def __init__(self, api_key: str = FIRECRAWL_API_KEY):
        self.api_key = api_key

    def is_configured(self):
        return bool(self.api_key)

    def search(self, query, *, search_type="web", num=8, country=None, time_range="any"):
        source = "news" if search_type == "news" else "web"
        payload = {"query": query, "sources": [source], "limit": num}
        if time_range in TIME_RANGES:
            payload["tbs"] = TIME_RANGES[time_range]
        if country:
            payload["country"] = country.lower()

        try:
            response = httpx.post(
                ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise SearchError(f"Firecrawl request failed: {error}") from error

        if response.status_code == 401:
            raise SearchError("Firecrawl rejected the API key. Check FIRECRAWL_API_KEY in .env.")
        if response.status_code in (402, 429):
            raise SearchError("Firecrawl rate limit or credits exhausted. Try again later.")
        if response.status_code >= 400:
            raise SearchError(f"Firecrawl error {response.status_code}: {response.text[:200]}")

        data = response.json()
        if not data.get("success", True):
            raise SearchError(f"Firecrawl error: {data.get('error', 'unknown error')}")

        items = (data.get("data") or {}).get(source, [])
        results = [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=_snippet(item.get("snippet") or item.get("description") or ""),
                date=item.get("date"),
            )
            for item in items[:num]
            if item.get("url")
        ]
        return SearchResponse(query=query, provider=self.name, results=results)


def _snippet(text):
    """Descriptions can be raw page text with markdown; make one clean line."""
    text = re.sub(r"[#*_`>\[\]]+", " ", text)
    text = " ".join(text.split())
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1].rstrip() + "…"
