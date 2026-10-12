# Web search

Butler can search the web for anything current or factual: news, live scores, prices, weather, release dates, people, companies. Answers say **how recent** the information is and **cite their sources** as links.

Web search supports several providers: **Serper** (Google results), **Tavily** (search built for AI agents) and **Firecrawl**. Configure any of them; one is used first and the others are automatic **fallbacks** if it fails.

## What you can ask

```
What's the score in India vs West Indies?
Any news about ISRO today?
Latest iPhone price in India?
Who won the F1 race yesterday?
Is the metro running on Sunday?
```

Butler decides when to search. It **doesn't** search for:
- your own data (mail, calendar, todos, Swiggy), which has its own tools
- stable general knowledge ("capital of Australia")

## Setup

Configure **one or both** providers in `.env`, then restart Butler.

**Serper** (Google results): sign up at [serper.dev](https://serper.dev), which has a free tier.

```
SERPER_API_KEY=your-key
```

**Tavily** (AI search with its own summarised answer): sign up at [tavily.com](https://tavily.com), which has a free tier.

```
TAVILY_API_KEY=tvly-…
TAVILY_SEARCH_DEPTH=basic      # basic = 1 credit per search; advanced = 2 credits, more relevant
```

**Firecrawl** (web and news search): sign up at [firecrawl.dev](https://firecrawl.dev). Each search uses 2 credits.

```
FIRECRAWL_API_KEY=fc-…
```

**Choosing between them:**

```
WEB_SEARCH_PROVIDER=serper     # which to try first: serper, tavily or firecrawl (default: serper)
WEB_SEARCH_COUNTRY=in          # optional: localise results (in, us, gb…)
```

The web UI's **Integrations** page then shows, for example, **Web search: Connected. Using serper. Fallback: tavily.**

Without a key, web search is simply off: Butler prints `NOTE: web search is off…` at startup and answers from its own knowledge.

## The `web_search` tool

| Argument | Values | Notes |
|---|---|---|
| `query` | Text | A focused query; Butler rewrites your sentence into one |
| `search_type` | `web` (default), `news` | `news` returns recent articles with publisher and age |
| `num_results` | 1–10 | Default 8 |
| `time_range` | `any`, `day`, `week`, `month`, `year` | Butler uses `day` for live scores and breaking news |
| `country` | 2-letter code | Defaults to `WEB_SEARCH_COUNTRY` |

Results come back in one shape, whatever the provider:

```json
{
  "query": "india vs west indies score",
  "provider": "serper",
  "answer": "…Google's answer box or knowledge panel, when there is one…",
  "results": [
    {"title": "IND vs WI, 3rd T20I…", "url": "https://…", "snippet": "India won by 14 runs…",
     "date": "16 hours ago", "source": "Indian Express"}
  ]
}
```

Each search costs one credit (two for Tavily `advanced` and for Firecrawl). Butler usually needs one search per question; a fallback attempt costs a credit on the second provider too.

## Providers

| Provider | Setting | Good at | Notes |
|---|---|---|---|
| **Serper** (Google) | `SERPER_API_KEY` | Fresh Google results, Google's answer box and knowledge panel, news | Web and news; country (`gl`); time filter |
| **Tavily** | `TAVILY_API_KEY` | A ready-made summary answer; page excerpts | Web and news (`topic`); time range; country boost (web only); `TAVILY_SEARCH_DEPTH` |
| **Firecrawl** | `FIRECRAWL_API_KEY` | Web and news results; part of the Firecrawl scraping platform | Web and news; time filter; country. 2 credits per search; Butler doesn't scrape pages (that would cost more). The `alexandria` source indexes software tools, not web pages, so `web_search` doesn't use it |

### Turning providers on and off

On the web UI's **Integrations** page, the **Web search** card lists every provider:

- **Switch** a provider on or off. Providers without an API key show *No API key* and can't be switched on.
- **Use first** makes that provider the one Butler tries first. The other providers that are on become fallbacks.
- **Changes apply immediately** to the web UI and the Telegram bot, with no restart. They're saved in `data/butler.db` and survive restarts.
- **Everything off:** the card says *All providers are switched off*, and Butler answers without searching until you switch one back on.

**Which one is used:**
- **First:** the provider you chose with **Use first**; if you haven't chosen, `WEB_SEARCH_PROVIDER`; otherwise the first provider in the registry that has a key (Serper, then Tavily, then Firecrawl).
- **Switched-off providers** are never used, even as a fallback.
- **Fallback:** if a search fails (bad key, credits used up, outage), the next configured provider is tried automatically. You only see an error if **all** of them fail.
- **Which answered:** each result carries `"provider"`.

Tavily returns long page excerpts; Butler trims each to about 500 characters to keep conversations small.

### Adding a provider

Each provider is one file. The agent, prompt, tool and UI don't change.

1. **Create `butler/integrations/websearch/providers/<name>.py`** with a subclass of `SearchProvider`:

   ```python
   import httpx
   from butler.config import EXAMPLE_API_KEY
   from ..base import SearchError, SearchProvider, SearchResponse, SearchResult

   class ExampleProvider(SearchProvider):
       name = "example"

       def __init__(self, api_key=EXAMPLE_API_KEY):
           self.api_key = api_key

       def is_configured(self):
           return bool(self.api_key)

       def search(self, query, *, search_type="web", num=8, country=None, time_range="any"):
           try:
               r = httpx.get("https://api.example.com/search",
                             params={"q": query, "count": num},
                             headers={"Authorization": f"Bearer {self.api_key}"}, timeout=15)
           except httpx.HTTPError as error:
               raise SearchError(f"Example request failed: {error}") from error
           if r.status_code in (401, 403):
               raise SearchError("Example rejected the API key. Check EXAMPLE_API_KEY in .env.")
           r.raise_for_status()
           return SearchResponse(
               query=query, provider=self.name,
               results=[SearchResult(title=i["title"], url=i["url"], snippet=i.get("description", ""))
                        for i in r.json()["results"]],
           )
   ```

   - Map the provider's fields onto `SearchResult` (title, url, snippet, date, source).
   - Put any direct answer in `SearchResponse.answer`.
   - Support whichever of `search_type`, `country` and `time_range` the API offers, and ignore the rest.
   - Raise `SearchError` with a readable message on failure; it's shown to the model.

2. **Add its key** to [butler/config.py](../../butler/config.py) (`EXAMPLE_API_KEY = os.getenv(...)`) and to `.env.example`.
3. **Register it** in [registry.py](../../butler/integrations/websearch/registry.py):

   ```python
   PROVIDERS = {"serper": SerperProvider, "tavily": TavilyProvider,
                "firecrawl": FirecrawlProvider, "example": ExampleProvider}
   ```

   The order is the preference order when `WEB_SEARCH_PROVIDER` isn't set, and the fallback order. [tavily.py](../../butler/integrations/websearch/providers/tavily.py) is a good second example: it maps a different response shape, trims long content, and converts country codes.
4. **Export it** in `providers/__init__.py`, add a row to the table above, and test:

   ```bash
   python -c "from butler.integrations.websearch.providers import ExampleProvider; print(ExampleProvider().search('test').to_dict())"
   ```

## Good to know

- **Keep your key secret.** It's only read from `.env`, which is git-ignored. Never put it in code. If a key was shared somewhere public, regenerate it in the provider's dashboard.
- **Errors are readable.** A bad key, no credits left (`429`), or a network failure becomes a sentence Butler can relay ("Serper rejected the API key…").
- **API:** `GET /api/integrations/web-search` lists the providers and their state; `PUT` with `{"enabled": {"serper": false}, "primary": "tavily"}` changes it.
- **Where the code lives:** [`butler/integrations/websearch/`](../../butler/integrations/websearch/):
  - `base.py`: shared types and the provider interface
  - `providers/`: one file per provider
  - `registry.py`: picks the provider
  - `tools.py`: the agent's tool
