"""搜索与摘要工具——作为 Skill 的工具层被按需加载。"""

from typing import Optional

from google.adk.tools import ToolContext


def search_web(
    query: str,
    max_results: int = 3,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """Search the web for information on a given query.

    Args:
        query: The search query string. Must be non-empty.
        max_results: Maximum number of results to return (1-5).
    """
    if not query or not query.strip():
        return {"error": "Query must be non-empty."}
    if not 1 <= max_results <= 5:
        return {"error": f"max_results must be 1-5, got {max_results}."}

    results = [
        {
            "title": f"Result {i + 1} for '{query}'",
            "snippet": f"Key insight {i + 1} about {query} — "
            f"detailed analysis and expert perspective on this topic...",
            "relevance": round(0.95 - i * 0.1, 2),
        }
        for i in range(max_results)
    ]

    if tool_context:
        count = tool_context.state.get("search_count", 0) + 1
        tool_context.state["search_count"] = count
        tool_context.state["last_query"] = query

    return {"query": query, "results": results, "count": len(results)}


def summarize_text(
    text: str,
    max_length: int = 200,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """Summarize a piece of text into a shorter version.

    Args:
        text: The text to summarize. Must be non-empty.
        max_length: Target maximum character length for the summary.
    """
    if not text or not text.strip():
        return {"error": "Text must be non-empty."}

    if len(text) <= max_length:
        summary = text
    else:
        summary = text[:max_length].rsplit(" ", 1)[0] + "..."

    if tool_context:
        count = tool_context.state.get("summarize_count", 0) + 1
        tool_context.state["summarize_count"] = count

    return {
        "summary": summary,
        "original_length": len(text),
        "summary_length": len(summary),
    }
