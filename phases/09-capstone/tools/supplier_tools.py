"""供应商数据库搜索——Tier 2，模拟 PostgreSQL 全文搜索。

关键模式：
  - 多查询变体：3-5 个语义相关的查询，提高召回率
  - 合并 catalog 结果后判断是否继续级联
  - 去重逻辑：按 supplier id 去重
"""

import json
from pathlib import Path

from google.adk.tools import ToolContext

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(filename: str) -> list | dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _matches_supplier(supplier: dict, query: str, category: str) -> bool:
    """判断供应商是否匹配查询。"""
    q = query.lower()
    # 匹配名称
    if q in supplier["name"].lower():
        return True
    # 匹配品类
    if category and category.lower() in [c.lower() for c in supplier.get("categories", [])]:
        return True
    # 匹配主营产品（如果有）
    if q in supplier.get("main_products", "").lower():
        return True
    return False


def _deduplicate(suppliers: list[dict]) -> list[dict]:
    """按 id 去重。"""
    seen = set()
    unique = []
    for s in suppliers:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    return unique


def search_suppliers(queries: list[str], category: str, tool_context: ToolContext) -> dict:
    """Search supplier database with multiple query variations.

    Uses 3-5 semantically related queries to improve recall (replicating
    the multi-query strategy from production systems).

    Args:
        queries: 3-5 semantically related search queries for the same product need.
        category: Product category for filtering (e.g., 'steel', 'electronics').
    """
    suppliers = _load_json("suppliers.json")

    all_matches = []
    for q in queries:
        matches = [s for s in suppliers if _matches_supplier(s, q, category)]
        all_matches.extend(matches)

    unique = _deduplicate(all_matches)

    # 合并 catalog 结果
    catalog_results = tool_context.state.get("catalog_results", [])
    combined = catalog_results + unique

    tool_context.state["supplier_results"] = unique
    tool_context.state["all_results"] = combined

    # --- 级联逻辑 ---
    if len(combined) < 5:
        tool_context.state["supplier_db_exhausted"] = True
        tool_context.actions.transfer_to_agent = "web_search_agent"
        cascade_note = f"Combined {len(combined)} results still insufficient, escalating to web search."
    else:
        tool_context.state["ready_for_qa"] = True
        cascade_note = ""

    return {
        "queries_used": queries,
        "category": category,
        "results": unique[:15],
        "combined_total": len(combined),
        "cascade_note": cascade_note,
    }
