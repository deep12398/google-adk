# Step 3: 3 级级联搜索

## 教学目标

- **Phase 06** State 标志驱动流程控制
- **Phase 03** `tool_context.actions.transfer_to_agent` 自动转移

## 学到什么

用 `tool_context.state` 标志实现 3 级级联搜索：catalog → supplier DB → web。
当某层搜索结果不足时，工具函数自动设置标志并触发 `transfer_to_agent`，
无需 orchestrator 显式判断。这是 axon_ai 的核心架构模式。

## 核心概念

```
级联搜索     — Tier 1 不足 → 自动降级到 Tier 2 → 再不足降级到 Tier 3
State 标志   — catalog_exhausted / supplier_db_exhausted / ready_for_qa
transfer_to_agent — 工具函数内触发 Agent 转移（不经过 orchestrator）
多查询变体   — supplier_search 用 3-5 个语义变体提高召回率
```

## 级联逻辑图

```
catalog_search_agent
  → search_catalog()
  → results ≥ 5?
    YES → state['ready_for_qa'] = True, state['all_results'] = results
    NO  → state['catalog_exhausted'] = True
        → transfer_to_agent = "supplier_search_agent"

supplier_search_agent
  → search_suppliers(queries=[5个变体])
  → combined (catalog + supplier) ≥ 5?
    YES → state['ready_for_qa'] = True
    NO  → state['supplier_db_exhausted'] = True
        → transfer_to_agent = "web_search_agent"

web_search_agent
  → search_external()
  → state['ready_for_qa'] = True（兜底，总是成功）
```

## State 标志表

| 标志 | 类型 | 设置者 | 含义 |
|------|------|--------|------|
| `catalog_results` | list | catalog_search | Tier 1 搜索结果 |
| `catalog_exhausted` | bool | catalog_search | Tier 1 不足（<5），触发 Tier 2 |
| `supplier_results` | list | supplier_search | Tier 2 搜索结果 |
| `supplier_db_exhausted` | bool | supplier_search | Tier 2 合并不足，触发 Tier 3 |
| `web_results` | list | web_search | Tier 3 搜索结果 |
| `all_results` | list | 各 search agent | 累积的所有搜索结果 |
| `ready_for_qa` | bool | search agents | 搜索完成，结果充足 |

## 创建文件清单

```
新建:
  tools/supplier_tools.py         # search_suppliers（多查询变体）
  tools/web_tools.py              # search_external（模拟外部搜索）
  agents/supplier_search_agent.py
  agents/web_search_agent.py

修改:
  tools/catalog_tools.py          # 添加级联标志 + transfer
  agents/orchestrator.py          # 添加 3 个搜索 Agent + 级联指令
  apps/app.py                     # 添加 STEP="3"
```

## 代码实现

### tools/catalog_tools.py（升级）

在 `search_catalog` 末尾添加级联逻辑：

```python
def search_catalog(query: str, tool_context: ToolContext) -> dict:
    """Search the product catalog by keyword (simulated vector search).

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
    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    tool_context.state["catalog_results"] = results[:10]
    tool_context.state["search_count"] = tool_context.state.get("search_count", 0) + 1
    tool_context.state["last_query"] = query

    # --- 级联逻辑 ---
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
```

### tools/supplier_tools.py

```python
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
```

### tools/web_tools.py

```python
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
```

### agents/supplier_search_agent.py

```python
"""Tier 2 供应商数据库搜索 Agent。"""

from google.adk.agents.llm_agent import LlmAgent
from tools.supplier_tools import search_suppliers

supplier_search_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="supplier_search_agent",
    description="Searches the internal supplier database (Tier 2 cascade).",
    instruction=(
        "You are a supplier database search specialist.\n\n"
        "You are called when the product catalog has insufficient results.\n"
        "1. Generate 3-5 semantic query variations from the user's need.\n"
        "2. Call search_suppliers with the queries and category.\n"
        "3. Report results including both catalog and supplier matches.\n"
    ),
    tools=[search_suppliers],
)
```

### agents/web_search_agent.py

```python
"""Tier 3 外部搜索 Agent。"""

from google.adk.agents.llm_agent import LlmAgent
from tools.web_tools import search_external

web_search_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="web_search_agent",
    description="Searches external sources like Alibaba (Tier 3 fallback).",
    instruction=(
        "You are a web search specialist for sourcing.\n\n"
        "You are called when internal databases have insufficient results.\n"
        "1. Use search_external to find suppliers on external platforms.\n"
        "2. Clearly mark results as external and advise verification.\n"
    ),
    tools=[search_external],
)
```

### agents/orchestrator.py（Step 3 升级）

```python
sourcing_orchestrator = LlmAgent(
    model="gemini-2.0-flash",
    name="sourcing_orchestrator",
    description="Routes user requests with 3-tier cascade search.",
    instruction=(
        "You are the sourcing assistant orchestrator.\n\n"
        "## Routing Rules\n"
        "1. FIRST: delegate to intent_agent to classify intent.\n"
        "2. For 'search' intent, use the 3-TIER CASCADE:\n"
        "   - Start with catalog_search_agent (Tier 1: internal catalog)\n"
        "   - The cascade happens AUTOMATICALLY via state flags:\n"
        "     * catalog_exhausted → supplier_search_agent (Tier 2)\n"
        "     * supplier_db_exhausted → web_search_agent (Tier 3)\n"
        "   - You don't need to manage the cascade manually.\n"
        "3. For 'chitchat' → delegate to chitchat_agent\n"
        "4. Tell the user which tier the results came from.\n"
    ),
    sub_agents=[
        intent_agent, catalog_search_agent, supplier_search_agent,
        web_search_agent, chitchat_agent,
    ],
)
```

## 验证

```bash
cd phases/09-capstone

# Tier 1 命中（catalog 有充足 steel 产品）：
STEP=3 PROMPT="Find stainless steel sheets" python apps/main.py

# Tier 1→2 级联（catalog 中 titanium 产品不足）：
STEP=3 PROMPT="Find titanium alloy products" python apps/main.py

# Tier 1→2→3 全级联（完全没有的产品）：
STEP=3 PROMPT="Find carbon fiber composite panels" python apps/main.py
```

**观察要点：**
- Tier 1 不足时，是否自动跳转到 supplier_search_agent
- `cascade_note` 字段是否正确显示级联原因
- `all_results` 是否正确累积各层结果

## 你应该理解的

1. `tool_context.actions.transfer_to_agent` 在工具函数内触发 Agent 转移
2. 这种转移绕过 orchestrator，直接从一个 Agent 跳到另一个
3. State 标志是 Agent 间通信的核心机制（而非消息传递）
4. 多查询变体策略提高搜索召回率（3-5 个语义相关查询）
5. 级联设计的关键：每层都能独立工作，也能作为整体级联
