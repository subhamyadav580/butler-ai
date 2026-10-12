"""Provider-neutral types for web search.

Every provider turns its own API response into these, so the agent's tool,
the prompt and the UI never depend on one provider's JSON shape.
"""

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

SearchType = Literal["web", "news"]
TimeRange = Literal["any", "day", "week", "month", "year"]


class SearchError(Exception):
    """A provider failed (bad key, quota, network). The message is shown to the LLM."""


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    date: Optional[str] = None        # as the provider gives it: "6 hours ago", "2026-10-11"
    source: Optional[str] = None      # site or publisher name, mainly for news


@dataclass
class SearchResponse:
    query: str
    provider: str
    results: list[SearchResult] = field(default_factory=list)
    # A direct answer when the provider has one (Google's answer box,
    # knowledge panel, live score card…): often enough to answer outright
    answer: Optional[str] = None

    def to_dict(self):
        data = asdict(self)
        return {k: v for k, v in data.items() if v not in (None, [], "")}


class SearchProvider:
    """Interface every provider implements (see providers/serper.py)."""

    name: str = ""
    title: str = ""           # shown in the UI
    key_setting: str = ""     # the .env variable holding its API key

    def is_configured(self) -> bool:
        """True when the provider has what it needs (e.g. an API key)."""
        raise NotImplementedError

    def search(
        self,
        query: str,
        *,
        search_type: SearchType = "web",
        num: int = 8,
        country: Optional[str] = None,
        time_range: TimeRange = "any",
    ) -> SearchResponse:
        raise NotImplementedError
