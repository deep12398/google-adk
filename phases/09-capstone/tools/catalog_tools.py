"""产品目录搜索工具——模拟 Pinecone 向量搜索。

关键模式：
  - _load_json(): 从 data/ 目录加载 JSON
  - search_catalog(): 带 ToolContext 的搜索函数
  - 搜索结果写入 tool_context.state（供后续 Agent 读取）
"""

import json
from pathlib import Path

from google.adk.tools import ToolContext

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(filename: str) -> list | dict:
    """加载 data/ 目录下的 JSON 文件。"""
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def search_catalog(query: str, tool_context: ToolContext) -> dict:
    """Search the product catalog by keyword (simulated vector search).

    Matches against product name, category, specs values, and tags.
    Results are sorted by relevance score (descending).
    If fewer than 5 results found, automatically cascades to supplier search.

    Args:
        query: Search keywords (product name, material, specs).
    """
    catalog = _load_json("catalog.json")
    q = query.lower()

    results = [
        p for p in catalog
        if q in p["name"].lower()
        or q in p.get("category", "").lower()
        or any(q in str(v).lower() for v in p.get("specs", {}).values())
        or any(q in t.lower() for t in p.get("tags", []))
    ]

    # 按 score 降序排列（模拟向量相似度排序）
    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 写入 state（供后续 Agent 或回调读取）
    tool_context.state["catalog_results"] = results[:10]
    tool_context.state["search_count"] = tool_context.state.get("search_count", 0) + 1
    tool_context.state["last_query"] = query

    # --- 级联逻辑（Step 3）---
    if len(results) < 5:
        tool_context.state["catalog_exhausted"] = True
        tool_context.actions.transfer_to_agent = "supplier_search_agent"
        cascade_note = f"Only {len(results)} results found, escalating to supplier database search."
    else:
        tool_context.state["ready_for_qa"] = True
        tool_context.state["all_results"] = results[:10]
        cascade_note = ""

    return {
        "query": query,
        "results": results[:10],
        "total": len(results),
        "cascade_note": cascade_note,
    }
