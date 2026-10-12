"""Web search settings, from .env."""

import os

import butler.config  # noqa: F401  (loads .env before the reads below)

# Which provider to try first: "serper", "tavily", "firecrawl". Empty = the
# first one with a key. The web UI's Integrations page can override this.
WEB_SEARCH_PROVIDER = os.getenv("WEB_SEARCH_PROVIDER", "").strip().lower()

# Default country for results (2-letter code, e.g. "in", "us"). Empty = provider default.
WEB_SEARCH_COUNTRY = os.getenv("WEB_SEARCH_COUNTRY", "").strip().lower()

# Provider API keys: any provider with a key is available
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "").strip()

# Tavily: "basic" (1 credit per search) or "advanced" (2 credits, more relevant)
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "basic").strip().lower()
