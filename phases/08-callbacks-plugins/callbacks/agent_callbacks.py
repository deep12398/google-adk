"""Agent 级回调——before_agent / after_agent。

演示：
  - before_agent_callback：记录请求开始、读取 state
  - after_agent_callback：记录耗时、写入 state

回调签名（ADK 使用关键字参数调用）：
  (*, callback_context: CallbackContext) → Optional[types.Content]
  返回 None = 继续执行
  返回 Content = 跳过 Agent（before）/ 追加响应（after）
"""

import time
from typing import Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext


def before_agent_callback(
    *, callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Agent 执行前回调。

    - 记录 Agent 启动日志
    - 读取 session state 中的用户偏好
    - 在 state 中记录开始时间
    """
    ctx = callback_context
    user_name = ctx.state.get("user:name", "anonymous")
    print(f"  [before_agent] Agent '{ctx.agent_name}' starting, user={user_name}")

    # 在 state 中记录开始时间（temp: 前缀表示临时数据）
    ctx.state["temp:agent_start_time"] = time.time()

    # 返回 None → 继续执行 Agent
    # 如果返回 Content → 跳过 Agent 执行，直接以该 Content 作为响应
    return None


def after_agent_callback(
    *, callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Agent 执行后回调。

    - 计算并记录 Agent 执行耗时
    - 在 state 中记录调用次数
    """
    ctx = callback_context
    start_time = ctx.state.get("temp:agent_start_time", 0)
    elapsed = time.time() - start_time if start_time else 0.0

    # 累加调用计数
    call_count = ctx.state.get("app:agent_call_count", 0) + 1
    ctx.state["app:agent_call_count"] = call_count

    print(f"  [after_agent] Agent '{ctx.agent_name}' done in {elapsed:.3f}s (call #{call_count})")

    # 返回 None → 不追加额外响应
    return None


# --- 演示：返回非 None 的效果 ---


def blocking_agent_callback(
    *, callback_context: CallbackContext,
) -> Optional[types.Content]:
    """演示 before_agent 返回 Content → 跳过 Agent 执行。

    这个回调不会在主流程中使用，仅用于教学演示。
    """
    return types.Content(
        parts=[types.Part.from_text(text="[BLOCKED] Agent execution was skipped by before_agent_callback.")],
        role="model",
    )
