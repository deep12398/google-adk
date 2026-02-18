"""研究工具——search_web 复用 + session state 追踪。

与 Phase 05 的 search_tool 类似，但增加了：
  - 每次搜索自动递增 app:total_searches 计数器
  - 搜索历史写入 session scope 的 search_history
"""

from google.adk.tools import ToolContext


def search_web(query: str, tool_context: ToolContext) -> dict:
    """搜索网络获取信息（模拟）。

    Args:
        query: 搜索关键词。
    """
    # 递增全局搜索计数
    count = tool_context.state.get("app:total_searches", 0)
    tool_context.state["app:total_searches"] = count + 1

    # 追踪本次 session 的搜索历史
    history = list(tool_context.state.get("search_history", []))
    history.append(query)
    tool_context.state["search_history"] = history

    # 模拟搜索结果
    return {
        "query": query,
        "results": [
            {
                "title": f"Latest developments in {query}",
                "snippet": f"Recent research shows significant progress in {query}. "
                f"Key findings include new frameworks, improved performance, "
                f"and broader industry adoption.",
                "source": "research-journal.example.com",
            },
            {
                "title": f"{query}: Industry Report 2025",
                "snippet": f"The {query} market is projected to grow significantly. "
                f"Major players are investing heavily in R&D.",
                "source": "industry-analysis.example.com",
            },
        ],
        "search_count": count + 1,
    }


def summarize_findings(topic: str, tool_context: ToolContext) -> dict:
    """将研究发现整理为结构化摘要，并保存到 session state。

    Args:
        topic: 研究主题。
    """
    history = tool_context.state.get("search_history", [])
    summary = (
        f"Research summary for '{topic}':\n"
        f"- Conducted {len(history)} searches\n"
        f"- Key themes: innovation, market growth, regulatory developments\n"
        f"- Searches performed: {', '.join(history) if history else 'none'}"
    )
    tool_context.state["research_summary"] = summary
    return {"topic": topic, "summary": summary}
