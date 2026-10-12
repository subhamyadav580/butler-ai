"""Web search as a Butler integration: one tool, pluggable providers."""

from butler.integrations.base import Integration

from .registry import any_configured, get_providers
from .tools import web_search

RULES = (
    "Web search (web_search):\n"
    "- Use it for anything current or that you aren't sure of: news, live "
    "scores, prices, weather, opening hours, recent releases, 'latest…'. "
    "Don't search for the user's own data (mail, calendar, todos, Swiggy): "
    "use those tools instead. Don't search for stable general knowledge you "
    "already know.\n"
    "- Write a focused query, not the user's whole sentence. For live or "
    "breaking things use time_range='day'; for news use search_type='news'.\n"
    "- If the result has an 'answer', it's usually the direct answer. Check "
    "dates on results; prefer the most recent for scores and news, and say "
    "how recent the information is.\n"
    "- Cite 1-3 sources as markdown links [site](url). Never invent facts "
    "that aren't in the results; if they don't answer it, say so.\n"
)


class WebSearchIntegration(Integration):
    name = "web_search"
    title = "Web search"
    description = "Current info from the web: news, scores, prices, facts. Answers cite their sources."
    tool_labels = {"web_search": "Searching the web"}
    examples = ["What's the latest news on ISRO?"]

    async def load_tools(self):
        # The tool stays loaded even when every provider is switched off in the
        # UI, so switching one back on works without a restart
        if not any_configured():
            return [], "web search is off. Add SERPER_API_KEY, TAVILY_API_KEY or FIRECRAWL_API_KEY to .env to enable it"
        return [web_search], None

    def rules(self, tool_names):
        return RULES

    def status(self, loaded_tool_names):
        try:
            providers = get_providers()
        except ValueError as error:   # unknown WEB_SEARCH_PROVIDER
            return {"state": "needs_setup", "detail": str(error)}
        if not providers and any_configured():
            return {"state": "disconnected", "detail": "All providers are switched off. Turn one on below."}
        if not providers:
            return {
                "state": "needs_setup",
                "detail": "Add SERPER_API_KEY, TAVILY_API_KEY or FIRECRAWL_API_KEY to .env, then restart Butler.",
            }
        names = [p.name for p in providers]
        detail = f"Using {names[0]}."
        if len(names) > 1:
            detail += f" Fallback: {', '.join(names[1:])}."
        return {"state": "connected", "detail": detail}


INTEGRATION = WebSearchIntegration()
