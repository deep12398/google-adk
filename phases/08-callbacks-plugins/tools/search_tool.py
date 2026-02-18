"""搜索工具（模拟）——被测 Agent 的工具。

与前面阶段的 search_web 相同，返回模拟搜索结果。
用于演示 tool 回调和插件的触发场景。
"""

from google.adk.tools import FunctionTool


def search_web(query: str) -> dict:
    """Search the web for information on a topic.

    Args:
        query: The search query string.

    Returns:
        A dict with search results.
    """
    return {
        "status": "success",
        "query": query,
        "results": [
            {
                "title": f"Latest developments in {query}",
                "snippet": (
                    f"Recent research shows significant progress in {query}. "
                    f"Key trends include automation, scalability, and integration."
                ),
            },
            {
                "title": f"{query} - Industry Report 2025",
                "snippet": (
                    f"The {query} market is projected to grow significantly. "
                    f"Major players are investing heavily in this space."
                ),
            },
        ],
    }


search_web_tool = FunctionTool(search_web)
