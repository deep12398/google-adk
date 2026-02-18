# Step 7: Q&A + 报价（完整工作流）

## 教学目标

- **Phase 03** output_key 实现 Agent 间数据传递
- 完整多 Agent 工作流串联

## 学到什么

添加 qa_agent（结果分析 + 供应商对比）和 quote_agent（报价生成 + artifact 保存），
完成从需求收集到报价输出的完整采购流程。
理解 `output_key` 如何让一个 Agent 的输出成为另一个 Agent 的输入。

## 核心概念

```
output_key   — Agent 的输出写入 state[key]，下游 Agent 通过 {key} 引用
完整工作流   — 意图 → 需求 → 搜索(级联) → Q&A → 报价
qa_agent     — 分析搜索结果、对比供应商、回答用户问题
quote_agent  — 根据需求 + 选定供应商生成报价单
```

## 完整工作流路径

```
用户: "I need 500 tons of 304 stainless steel, get me a quote"

1. orchestrator → intent_agent
   classify_intent → "search" (+ "quote")

2. orchestrator → requirements_agent
   infer_category → steel
   collect_requirements → {product, quantity, quality, ...}
   output_key: "requirements_summary" → state

3. orchestrator → catalog_search_agent
   search_catalog → results (如果不足则级联)
   state["all_results"] 累积

4. orchestrator → qa_agent
   分析 {all_results}，对比供应商
   output_key: "qa_output" → state

5. orchestrator → quote_agent
   读取 {requirements} + {all_results}
   generate_quote → 报价单
   save_document → artifact
   output_key: "quote_output" → state
```

## 创建文件清单

```
新建:
  tools/qa_tools.py               # compare_products, get_product_details
  tools/quote_tools.py            # generate_quote
  agents/qa_agent.py
  agents/quote_agent.py

修改:
  agents/orchestrator.py          # 完整 8 个 sub_agents + 全路由
  prompts/templates.py            # FULL_ROUTING_PROMPT
  apps/app.py                     # STEP="7"
```

## 代码实现

### tools/qa_tools.py

```python
"""Q&A 工具——产品对比 + 详情查询。"""

import json
from pathlib import Path
from google.adk.tools import ToolContext

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(filename: str) -> list | dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def compare_products(product_ids: str, tool_context: ToolContext) -> dict:
    """Compare multiple products side by side.

    Args:
        product_ids: Comma-separated product IDs (e.g., "P001,P002,P003").
    """
    catalog = _load_json("catalog.json")
    ids = [pid.strip() for pid in product_ids.split(",")]
    products = [p for p in catalog if p["id"] in ids]

    if len(products) < 2:
        return {"error": f"Need at least 2 products to compare. Found {len(products)} for IDs: {ids}"}

    tool_context.state["temp:last_comparison"] = ids

    return {
        "products": products,
        "comparison_dimensions": ["price_range", "moq", "lead_time_days", "specs", "supplier_id"],
        "count": len(products),
    }


def get_product_details(product_id: str, tool_context: ToolContext) -> dict:
    """Get detailed information about a specific product including supplier info.

    Args:
        product_id: The product ID (e.g., "P001").
    """
    catalog = _load_json("catalog.json")
    suppliers = _load_json("suppliers.json")

    product = next((p for p in catalog if p["id"] == product_id), None)
    if not product:
        return {"error": f"Product {product_id} not found."}

    # 补充供应商信息
    supplier = next((s for s in suppliers if s["id"] == product.get("supplier_id")), None)
    if supplier:
        product["supplier_details"] = supplier

    return product
```

### tools/quote_tools.py

```python
"""报价工具——生成结构化报价单。"""

from datetime import datetime, timezone
from google.adk.tools import ToolContext


def generate_quote(
    product_id: str,
    quantity: int,
    delivery_deadline: str = "",
    special_requirements: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Generate a price quote for a specific product.

    Reads requirements from state if available.

    Args:
        product_id: The product to quote.
        quantity: Number of units / tons requested.
        delivery_deadline: Requested delivery date (e.g., "2 weeks").
        special_requirements: Any special requirements (e.g., "mirror finish").
    """
    # 从 state 读取已收集的需求
    requirements = {}
    if tool_context:
        requirements = tool_context.state.get("requirements", {})

    quote = {
        "quote_id": f"Q-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "product_id": product_id,
        "quantity": quantity,
        "unit": requirements.get("unit", "tons"),
        "delivery_deadline": delivery_deadline or requirements.get("deadline", "TBD"),
        "special_requirements": special_requirements or requirements.get("quality", ""),
        "estimated_unit_price": "3,000 CNY/ton",  # 模拟
        "estimated_total": f"{3000 * max(quantity, 1):,} CNY",
        "validity": "7 days",
        "payment_terms": "30% deposit, 70% before shipment",
        "status": "draft",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if tool_context:
        tool_context.state["last_quote"] = quote

    return quote
```

### agents/qa_agent.py

```python
"""Q&A Agent——分析搜索结果、对比供应商。

output_key="qa_output" 将分析结果写入 state。
instruction 中引用 {all_results} 获取搜索结果。
"""

from google.adk.agents.llm_agent import LlmAgent
from tools.qa_tools import compare_products, get_product_details

qa_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="qa_agent",
    description="Analyzes search results, compares products and suppliers.",
    instruction=(
        "You are a sourcing Q&A specialist.\n\n"
        "## Your Capabilities\n"
        "- Compare products side by side using compare_products\n"
        "- Get detailed info on a product using get_product_details\n"
        "- Analyze and summarize search results\n\n"
        "## Available Context\n"
        "Search results: {all_results}\n\n"
        "## Guidelines\n"
        "- Present comparisons in table format\n"
        "- Highlight pros/cons of each option\n"
        "- Recommend the best option based on requirements\n"
    ),
    tools=[compare_products, get_product_details],
    output_key="qa_output",
)
```

### agents/quote_agent.py

```python
"""报价 Agent——生成报价单 + 保存为 artifact。

使用 save_document（来自 memory_tools.py）将报价保存为版本化 artifact。
instruction 引用 {requirements} 获取需求上下文。
"""

from google.adk.agents.llm_agent import LlmAgent
from tools.quote_tools import generate_quote
from tools.memory_tools import save_document

quote_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="quote_agent",
    description="Generates price quotes based on requirements and selected products.",
    instruction=(
        "You are a quote generation specialist.\n\n"
        "## Workflow\n"
        "1. Review the user's requirements: {requirements}\n"
        "2. Use generate_quote to create a formal quote.\n"
        "3. Save the quote document using save_document.\n"
        "4. Present the quote summary to the user.\n\n"
        "## Format\n"
        "Present quotes professionally with all key terms.\n"
    ),
    tools=[generate_quote, save_document],
    output_key="quote_output",
)
```

### prompts/templates.py（完整路由 Prompt）

```python
"""共享 Prompt 模板。"""

FULL_ROUTING_PROMPT = (
    "You are the sourcing assistant orchestrator.\n\n"
    "## Agent Routing by Intent\n"
    "1. ALWAYS start by delegating to intent_agent to classify intent.\n"
    "2. Route based on classified intent:\n"
    "   - 'search' → 3-tier cascade:\n"
    "     * Start with catalog_search_agent\n"
    "     * Cascade is automatic via state flags\n"
    "   - 'requirements' → requirements_agent\n"
    "   - 'qa' or 'compare' → qa_agent\n"
    "   - 'quote' → quote_agent (ensure requirements collected first)\n"
    "   - 'chitchat' → chitchat_agent\n\n"
    "## Workflow for Complex Requests\n"
    "If the user wants a full sourcing workflow (search + quote):\n"
    "1. requirements_agent → collect and categorize\n"
    "2. catalog_search_agent → search (with automatic cascade)\n"
    "3. qa_agent → analyze results\n"
    "4. quote_agent → generate quote\n\n"
    "## State Keys Available\n"
    "- {requirements} — collected requirements\n"
    "- {all_results} — accumulated search results\n"
    "- {qa_output} — Q&A analysis\n"
    "- {classified_intent} — intent classification\n"
)
```

### orchestrator.py（Step 7 完整版）

```python
from google.adk.agents.llm_agent import LlmAgent
from agents.intent_agent import intent_agent
from agents.requirements_agent import requirements_agent
from agents.catalog_search_agent import catalog_search_agent
from agents.supplier_search_agent import supplier_search_agent
from agents.web_search_agent import web_search_agent
from agents.qa_agent import qa_agent
from agents.quote_agent import quote_agent
from agents.chitchat_agent import chitchat_agent
from prompts.templates import FULL_ROUTING_PROMPT
# + callbacks imports (from Step 5)

sourcing_orchestrator = LlmAgent(
    model="gemini-2.0-flash",
    name="sourcing_orchestrator",
    description="Full sourcing assistant with 8 specialized sub-agents.",
    instruction=FULL_ROUTING_PROMPT,
    sub_agents=[
        intent_agent, requirements_agent,
        catalog_search_agent, supplier_search_agent, web_search_agent,
        qa_agent, quote_agent, chitchat_agent,
    ],
    # callbacks from Step 5
    before_agent_callback=before_agent_cb,
    after_agent_callback=after_agent_cb,
    before_model_callback=before_model_cb,
    after_model_callback=after_model_cb,
    on_model_error_callback=on_model_error_cb,
)
```

## 验证

```bash
cd phases/09-capstone

# Q&A 流程
STEP=7 PROMPT="Compare products P001 and P002" python apps/main.py

# 完整工作流
STEP=7 PROMPT="I need 500 tons of 304 stainless steel, ISO9001, deliver in 2 weeks, get me a quote" python apps/main.py
# 期望：intent → requirements → search → qa → quote → artifact saved
```

## 你应该理解的

1. `output_key="qa_output"` 让 qa_agent 的输出写入 `state["qa_output"]`
2. 其他 Agent 通过 `{qa_output}` 在 instruction 中引用该值
3. 这是 Agent 间数据流的主要机制（而非消息传递）
4. 完整工作流是多个 Agent 依次执行，通过 state 传递上下文
5. quote_agent 同时使用 generate_quote 和 save_document → 报价 + 持久化
