"""Tool 级回调——before_tool / after_tool / on_tool_error。

演示：
  - before_tool_callback：参数验证 + 日志
  - after_tool_callback：结果摘要 + 日志
  - on_tool_error_callback：fallback 结果

回调签名（ADK 使用关键字参数调用）：
  before: (*, tool, args, tool_context) → Optional[dict]
  after:  (*, tool, args, tool_context, tool_response) → Optional[dict]
  error:  (*, tool, args, tool_context, error) → Optional[dict]
"""

from typing import Any, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


def before_tool_callback(
    *, tool: BaseTool, args: dict[str, Any], tool_context: ToolContext,
) -> Optional[dict]:
    """工具调用前回调。

    - 打印工具名称和参数
    - 参数验证（可拒绝危险操作）
    """
    print(f"  [before_tool] Calling '{tool.name}' with args: {args}")

    # 参数验证示例：拒绝空查询
    if tool.name == "search_web" and not args.get("query", "").strip():
        print(f"  [before_tool] REJECTED: empty query")
        return {"status": "error", "message": "Query cannot be empty"}

    # 返回 None → 继续执行工具
    # 返回 dict → 跳过工具执行，用此 dict 作为结果
    return None


def after_tool_callback(
    *, tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: dict,
) -> Optional[dict]:
    """工具调用后回调。

    - 打印结果摘要
    - 在 state 中记录工具调用历史
    """
    ctx = tool_context

    # 结果摘要
    result_str = str(tool_response)
    summary = result_str[:100] + "..." if len(result_str) > 100 else result_str
    print(f"  [after_tool] '{tool.name}' returned: {summary}")

    # 记录工具调用历史
    tool_history = ctx.state.get("app:tool_history", [])
    tool_history.append({"tool": tool.name, "args": args})
    ctx.state["app:tool_history"] = tool_history

    # 返回 None → 保持原始结果
    # 返回 dict → 替换工具结果
    return None


def on_tool_error_callback(
    *, tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, error: Exception,
) -> Optional[dict]:
    """工具调用出错时的 fallback 回调。

    - 记录错误
    - 返回 fallback 结果（而不是抛异常）
    """
    print(f"  [on_tool_error] '{tool.name}' failed: {type(error).__name__}: {error}")

    # 返回 fallback 结果 → 抑制错误
    return {
        "status": "error",
        "message": f"Tool '{tool.name}' encountered an error: {error}",
        "fallback": True,
    }
