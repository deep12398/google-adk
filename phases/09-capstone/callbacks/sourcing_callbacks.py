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
