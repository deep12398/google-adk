# Step 5: 回调 + 搜索结果充实

## 教学目标

- **Phase 08** 9 种回调（before/after/error × agent/model/tool）
- **Phase 04** 回调实战：搜索结果自动充实（axon_ai enrichment_callback 模式）

## 学到什么

如何用回调实现横切关注点：搜索前验证 + 计时，搜索后自动充实结果，
Agent 级别追踪耗时，Model 级别统计 LLM 调用。
理解回调签名（keyword-only args）和返回值语义。

## 核心概念

```
9 种回调 = before/after/error × agent/model/tool

Tool callbacks（挂在 Agent 上）:
  before_tool_callback  — 工具调用前（验证、日志、计时）
  after_tool_callback   — 工具调用后（充实结果、统计）
  on_tool_error_callback — 工具出错时（降级、重试）

Agent callbacks:
  before_agent_callback — Agent 开始前
  after_agent_callback  — Agent 结束后

Model callbacks:
  before_model_callback   — LLM 调用前
  after_model_callback    — LLM 调用后
  on_model_error_callback — LLM 出错时

返回值语义:
  return None  → 不干预，继续正常流程
  return dict  → 拦截工具调用，直接返回该 dict（跳过实际执行）
  return Content → 拦截 Agent，直接返回该 Content
```

## 创建文件清单

```
新建:
  callbacks/
    __init__.py
    sourcing_callbacks.py     # 9 种回调全覆盖

修改:
  agents/catalog_search_agent.py    # 挂载 tool callbacks
  agents/supplier_search_agent.py   # 挂载 tool callbacks
  agents/web_search_agent.py        # 挂载 tool callbacks
  agents/orchestrator.py            # 挂载 agent/model callbacks
  apps/app.py                       # STEP="5"
```

## 代码实现

### callbacks/sourcing_callbacks.py

```python
"""采购助手回调——9 种回调全覆盖。

关键：所有回调使用 keyword-only args（*,）
这是 Phase 08 确立的签名约定。

按角色分类：
  1. Tool callbacks → 挂在搜索 Agent 上
  2. Agent callbacks → 挂在 orchestrator 上
  3. Model callbacks → 挂在 orchestrator 上
"""

import time
from typing import Any, Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


# ===== Tool Callbacks（挂在 search agents 上）=====

def before_tool_cb(
    *, tool: BaseTool, args: dict[str, Any], tool_context: ToolContext,
) -> Optional[dict]:
    """搜索前：参数验证 + 开始计时。

    - 拦截空查询（返回 error dict）
    - 记录开始时间到 temp: scope
    """
    # 计时
    tool_context.state["temp:search_start"] = time.time()

    # 验证：空查询拦截
    if tool.name.startswith("search_") and not args.get("query", "").strip():
        return {"error": "Query cannot be empty"}

    print(f"  [cb:before_tool] {tool.name}({list(args.keys())})")
    return None  # 不拦截，继续执行


def after_tool_cb(
    *, tool: BaseTool, args: dict[str, Any],
    tool_context: ToolContext, tool_response: dict,
) -> Optional[dict]:
    """搜索后：结果充实 + 耗时统计。

    复现 axon_ai 的 enrichment_callback：
    搜索工具返回后，自动为每条结果补充元数据。
    """
    # 耗时统计
    start = tool_context.state.get("temp:search_start", time.time())
    elapsed = time.time() - start
    print(f"  [cb:after_tool] {tool.name} done in {elapsed:.2f}s")

    # 充实结果
    if isinstance(tool_response, dict) and "results" in tool_response:
        for r in tool_response["results"]:
            if isinstance(r, dict):
                r["enriched"] = True
                r["search_tier"] = (
                    1 if "catalog" in tool.name
                    else 2 if "supplier" in tool.name
                    else 3
                )

    # 搜索次数统计（app: scope，跨用户）
    tool_context.state["app:search_count"] = (
        tool_context.state.get("app:search_count", 0) + 1
    )
    return None  # 不修改返回值


def on_tool_error_cb(
    *, tool: BaseTool, args: dict[str, Any],
    tool_context: ToolContext, error: Exception,
) -> Optional[dict]:
    """工具出错：日志 + 降级返回。"""
    print(f"  [cb:tool_error] {tool.name}: {type(error).__name__}: {error}")
    return {"error": str(error), "fallback": True}


# ===== Agent Callbacks（挂在 orchestrator 上）=====

def before_agent_cb(
    *, callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Agent 开始前：计时。"""
    callback_context.state["temp:agent_start"] = time.time()
    print(f"  [cb:before_agent] {callback_context.agent_name}")
    return None


def after_agent_cb(
    *, callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Agent 结束后：打印耗时。"""
    start = callback_context.state.get("temp:agent_start", time.time())
    elapsed = time.time() - start
    print(f"  [cb:after_agent] {callback_context.agent_name} ({elapsed:.2f}s)")
    return None


# ===== Model Callbacks（挂在 orchestrator 上）=====

def before_model_cb(
    *, callback_context: CallbackContext, llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """LLM 调用前：计数。"""
    callback_context.state["app:llm_call_count"] = (
        callback_context.state.get("app:llm_call_count", 0) + 1
    )
    return None


def after_model_cb(
    *, callback_context: CallbackContext, llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """LLM 调用后：打印 token 用量。"""
    if llm_response.usage_metadata:
        total = getattr(llm_response.usage_metadata, "total_token_count", 0) or 0
        print(f"  [cb:after_model] tokens={total}")
    return None


def on_model_error_cb(
    *, callback_context: CallbackContext,
    llm_request: LlmRequest, error: Exception,
) -> Optional[LlmResponse]:
    """LLM 出错：日志（不拦截，让上层处理）。"""
    print(f"  [cb:model_error] {type(error).__name__}: {error}")
    return None
```

### 挂载到 Agent

```python
# agents/catalog_search_agent.py（修改）
from callbacks.sourcing_callbacks import before_tool_cb, after_tool_cb, on_tool_error_cb

catalog_search_agent = LlmAgent(
    ...,
    before_tool_callback=before_tool_cb,
    after_tool_callback=after_tool_cb,
    on_tool_error_callback=on_tool_error_cb,
)

# agents/orchestrator.py（修改）
from callbacks.sourcing_callbacks import (
    before_agent_cb, after_agent_cb,
    before_model_cb, after_model_cb, on_model_error_cb,
)

sourcing_orchestrator = LlmAgent(
    ...,
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
STEP=5 PROMPT="Find stainless steel sheets" python apps/main.py
```

**期望输出（日志）：**
```
  [cb:before_agent] sourcing_orchestrator
  [cb:before_tool] classify_intent(['user_message'])
  [cb:after_tool] classify_intent done in 0.00s
  [cb:after_model] tokens=245
  [cb:before_tool] search_catalog(['query'])
  [cb:after_tool] search_catalog done in 0.01s
  [cb:after_agent] sourcing_orchestrator (2.34s)
```

搜索结果中每条记录应包含 `"enriched": true` 和 `"search_tier": 1`。

## 你应该理解的

1. 回调签名**必须用 keyword-only args**（`*, tool, args, tool_context`）
2. `return None` = 不干预；`return dict/Content` = 拦截
3. Tool callbacks 挂在**使用工具的 Agent** 上（不是工具本身）
4. Agent/Model callbacks 挂在该 Agent 自身
5. after_tool_callback 可以修改 tool_response → 实现结果充实
6. `temp:` scope 的 state 不会持久化 → 适合计时器等临时数据
