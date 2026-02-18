# Step 1: 骨架 + 模拟数据 + 单 Agent 搜索

## 教学目标

- **Phase 02** 项目骨架：App + sys.path + 目录约定
- **Phase 04** FunctionTool + ToolContext.state 基础

## 学到什么

从零搭建一个 ADK 项目，创建模拟数据（JSON），写第一个带 `ToolContext` 的搜索工具函数，
用 `InMemoryRunner` 运行并观察工具调用和状态变化。

## 核心概念

```
App          — ADK 应用容器，包含 root_agent
InMemoryRunner — 最简单的运行器，内存中管理 session
FunctionTool — 普通 Python 函数自动包装为工具
ToolContext   — 工具函数的上下文，可读写 state
```

## 创建文件清单

```
phases/09-capstone/
  __init__.py
  data/
    catalog.json          # ~20 个产品（含 score 模拟向量搜索排序）
    suppliers.json        # ~10 个供应商
    categories.json       # 品类层级 + 别名映射
  tools/
    __init__.py
    catalog_tools.py      # search_catalog + _load_json
  agents/
    __init__.py
    catalog_search_agent.py
  apps/
    __init__.py
    app.py                # App 定义 + STEP 路由
    main.py               # InMemoryRunner 入口
  docs/
    architecture.md
  README.md
```

## 数据设计

### data/catalog.json（~20 个产品）

模拟 Pinecone 向量搜索结果，每个产品带 `score` 字段用于排序。
品类覆盖：steel（钢材）、aluminum（铝材）、fasteners（紧固件）、packaging（包装）、electronics（电子）。

```json
[
  {
    "id": "P001",
    "name": "304 Stainless Steel Sheet 1mm",
    "category": "steel",
    "subcategory": "stainless",
    "specs": {"material": "304SS", "thickness": "1mm", "finish": "2B"},
    "supplier_id": "S001",
    "price_range": {"min": 2800, "max": 3200, "unit": "CNY/ton"},
    "moq": 5,
    "lead_time_days": 7,
    "tags": ["stainless", "sheet", "304"],
    "score": 0.95
  }
]
```

**要点：**
- `score` 模拟向量相似度，搜索后按 score 降序排列
- `tags` 用于扩展关键词匹配
- 数据量 ~20 条，确保有些查询能命中 ≥5 条，有些 <5 条（为 Step 3 级联做准备）

### data/suppliers.json（~10 个供应商）

```json
[
  {
    "id": "S001",
    "name": "Shanghai Steel Co.",
    "categories": ["steel", "aluminum"],
    "location": "Shanghai",
    "rating": 4.5,
    "certifications": ["ISO9001", "ISO14001"],
    "min_order_value": 10000,
    "verified": true
  }
]
```

### data/categories.json

```json
{
  "steel": {"aliases": ["stainless steel", "carbon steel", "steel sheet", "steel plate"], "parent": "metals"},
  "aluminum": {"aliases": ["aluminium", "aluminum alloy", "AL"], "parent": "metals"},
  "fasteners": {"aliases": ["bolts", "nuts", "screws", "washers"], "parent": "hardware"},
  "packaging": {"aliases": ["cartons", "boxes", "shrink wrap", "bubble wrap"], "parent": "consumables"},
  "electronics": {"aliases": ["PCB", "circuit board", "LED", "connector"], "parent": "components"}
}
```

## 代码实现

### tools/catalog_tools.py

```python
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

    return {
        "query": query,
        "results": results[:10],
        "total": len(results),
    }
```

### agents/catalog_search_agent.py

```python
"""产品目录搜索 Agent——Step 1 的唯一 Agent。

使用 LlmAgent（而非 Phase 01 的 Agent 别名），
因为后续 Step 会用到 LlmAgent 特有的参数（sub_agents, callbacks 等）。
"""

from google.adk.agents.llm_agent import LlmAgent
from tools.catalog_tools import search_catalog

catalog_search_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="catalog_search_agent",
    description="Searches the internal product catalog for matching items.",
    instruction=(
        "You are a sourcing assistant that helps users find products.\n\n"
        "When the user describes what they need:\n"
        "1. Use search_catalog with relevant keywords.\n"
        "2. Present results in a clear table format:\n"
        "   | Name | Specs | Price Range | MOQ | Lead Time |\n"
        "3. If no results found, suggest broadening or rephrasing the search.\n"
        "4. Mention the total number of matches found.\n"
    ),
    tools=[search_catalog],
)
```

### apps/app.py

```python
"""Phase 09 App 定义——STEP 路由模式。

通过 STEP 环境变量选择不同的 root_agent：
  STEP=1 → catalog_search_agent（单 Agent 搜索）
  STEP=2 → sourcing_orchestrator（意图识别 + 路由）
  ...

这个文件会随着每个 Step 增量修改，添加新的 Agent 选项。
"""

import os
import sys
from pathlib import Path

from google.adk.apps import App

# --- sys.path 设置（Phase 02 约定）---
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- Agent 导入 ---
from agents.catalog_search_agent import catalog_search_agent  # noqa: E402

# --- STEP 路由 ---
STEP = os.getenv("STEP", "1")

ROOT_AGENTS = {
    "1": catalog_search_agent,
}

root_agent = ROOT_AGENTS.get(STEP, catalog_search_agent)

app = App(
    name=f"sourcing_step{STEP}",
    root_agent=root_agent,
)
```

### apps/main.py

```python
"""Phase 09 入口——Step 1-5 使用 InMemoryRunner。

Step 6 起会切换到 Runner + DatabaseSessionService。
"""

import asyncio
import os

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner

from app import app

load_dotenv()

runner = InMemoryRunner(app=app)


async def main() -> None:
    prompt = os.getenv("PROMPT", "I need stainless steel sheets, 1mm thickness")
    events = await runner.run_debug(prompt)


if __name__ == "__main__":
    asyncio.run(main())
```

## 验证

```bash
cd phases/09-capstone
STEP=1 PROMPT="Find stainless steel sheets" python apps/main.py
```

**期望输出：**
- Agent 调用 `search_catalog(query="stainless steel sheets")`
- 返回匹配的产品，按 score 排序
- 输出包含表格格式的产品列表

## 你应该理解的

1. `App` 是 ADK 的容器，持有 `root_agent`
2. `InMemoryRunner` 管理 session 和事件循环
3. `ToolContext.state` 是工具间共享状态的核心机制
4. 工具函数的 `Args:` docstring 会被 ADK 解析为参数描述，传给 LLM
