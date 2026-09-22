"""
NexusAI Tool — Web Search (DuckDuckGo, no API key needed).
"""

from backend.agents.base_agent import Tool


async def _web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return f"No results found for: {query}"
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"{i}. **{r.get('title', 'No title')}**\n"
                    f"   {r.get('body', 'No description')}\n"
                    f"   URL: {r.get('href', 'N/A')}"
                )
            return "\n\n".join(formatted)
    except Exception as e:
        return f"Search error: {str(e)}"


web_search_tool = Tool(
    name="web_search",
    description="Search the web for information using DuckDuckGo. Returns titles, descriptions, and URLs.",
    parameters={
        "query": {"type": "string", "description": "The search query"},
        "max_results": {"type": "integer", "description": "Maximum results (default 5)"},
    },
    func=_web_search,
)
