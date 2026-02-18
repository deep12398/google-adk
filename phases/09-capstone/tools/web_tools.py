"""外部搜索——Tier 3，模拟 Alibaba/Made-in-China 爬虫。

Tier 3 是兜底层，总是返回结果并设置 ready_for_qa=True。
"""

from google.adk.tools import ToolContext


def search_external(query: str, tool_context: ToolContext) -> dict:
    """Search external sources for products/suppliers (simulated web crawl).

    This is the Tier 3 fallback when internal catalog and supplier DB
    return insufficient results. Always succeeds.

    Args:
        query: Search query for external product search.
    """
    # 模拟外部搜索结果
    results = [
        {
            "source": "alibaba.com",
            "title": f"{query} - Multiple Verified Suppliers",
            "snippet": f"Found 50+ suppliers for {query} on Alibaba with Trade Assurance.",
            "url": f"https://alibaba.com/trade/search?q={query.replace(' ', '+')}",
            "simulated": True,
        },
        {
            "source": "made-in-china.com",
            "title": f"{query} Manufacturers & Factories",
            "snippet": f"China {query} manufacturers, find quality products from verified factories.",
            "url": f"https://made-in-china.com/search/{query.replace(' ', '-')}",
            "simulated": True,
        },
    ]

    prev_results = tool_context.state.get("all_results", [])
    tool_context.state["web_results"] = results
    tool_context.state["all_results"] = prev_results + results
    tool_context.state["ready_for_qa"] = True  # Tier 3 兜底，总是设置 ready

    return {
        "query": query,
        "source": "external_web",
        "results": results,
        "note": "External web results — verify supplier credentials independently.",
    }
