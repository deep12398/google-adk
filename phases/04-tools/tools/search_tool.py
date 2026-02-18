import random
from typing import Optional

from google.adk.tools import ToolContext


def search_web(
    query: str,
    max_results: int = 3,
    language: str = "en",
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """Search the web for information on a given query.

    Args:
        query: The search query string. Must be non-empty.
        max_results: Maximum number of results to return (1-10).
        language: Language code for results (e.g. 'en', 'zh').
    """
    # --- Parameter validation (graceful error dict) ---
    if not query or not query.strip():
        return {"error": "Query must be non-empty."}
    if not 1 <= max_results <= 10:
        return {"error": f"max_results must be 1-10, got {max_results}."}

    # --- Simulated unreliable API (triggers on_tool_error_callback) ---
    if random.random() < 0.15:
        raise ConnectionError("Simulated: search API temporarily unavailable.")

    # --- Simulated results ---
    results = [
        {
            "title": f"Result {i + 1} for '{query}'",
            "snippet": f"Key insight {i + 1} about {query}...",
        }
        for i in range(max_results)
    ]

    # --- ToolContext: write search state ---
    if tool_context:
        search_count = tool_context.state.get("search_count", 0) + 1
        tool_context.state["search_count"] = search_count
        tool_context.state["last_query"] = query

    return {"query": query, "results": results, "count": len(results)}
