"""Serper (https://serper.dev): Google Search results over a simple JSON API."""

from typing import Optional

import httpx

from ..config import SERPER_API_KEY

from ..base import SearchError, SearchProvider, SearchResponse, SearchResult

ENDPOINTS = {
    "web": "https://google.serper.dev/search",
    "news": "https://google.serper.dev/news",
}

# Google's time filter (tbs=qdr:…)
TIME_RANGES = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}

TIMEOUT_SECONDS = 15


class SerperProvider(SearchProvider):
    name = "serper"
    title = "Serper (Google)"
    key_setting = "SERPER_API_KEY"

    def __init__(self, api_key: str = SERPER_API_KEY):
        self.api_key = api_key

    def is_configured(self):
        return bool(self.api_key)

    def search(self, query, *, search_type="web", num=8, country=None, time_range="any"):
        payload = {"q": query, "num": num}
        if country:
            payload["gl"] = country
        if time_range in TIME_RANGES:
            payload["tbs"] = TIME_RANGES[time_range]

        try:
            response = httpx.post(
                ENDPOINTS[search_type],
                json=payload,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise SearchError(f"Serper request failed: {error}") from error

        if response.status_code in (401, 403):
            raise SearchError("Serper rejected the API key. Check SERPER_API_KEY in .env.")
        if response.status_code == 429:
            raise SearchError("Serper rate limit or credits exhausted. Try again later.")
        if response.status_code >= 400:
            raise SearchError(f"Serper error {response.status_code}: {response.text[:200]}")

        data = response.json()
        items = data.get("news" if search_type == "news" else "organic", [])
        results = [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                date=item.get("date"),
                source=item.get("source"),
            )
            for item in items[:num]
            if item.get("link")
        ]
        return SearchResponse(query=query, provider=self.name,
                              results=results, answer=_direct_answer(data))


def _direct_answer(data) -> Optional[str]:
    """Google's answer box or knowledge panel, flattened to one line."""
    box = data.get("answerBox") or {}
    parts = [box.get("title"), box.get("answer"), box.get("snippet")]
    if not any(parts):
        graph = data.get("knowledgeGraph") or {}
        parts = [graph.get("title"), graph.get("type"), graph.get("description")]
    text = " — ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())
    return text or None
