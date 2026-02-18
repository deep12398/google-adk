"""Model 级回调——before_model / after_model / on_model_error。

演示：
  - before_model_callback：打印 prompt 摘要，可实现缓存
  - after_model_callback：打印 token 用量
  - on_model_error_callback：降级处理

回调签名（ADK 使用关键字参数调用）：
  before: (*, callback_context, llm_request) → Optional[LlmResponse]
  after:  (*, callback_context, llm_response) → Optional[LlmResponse]
  error:  (*, callback_context, llm_request, error) → Optional[LlmResponse]
"""

from typing import Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


def before_model_callback(
    *, callback_context: CallbackContext, llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """LLM 调用前回调。

    - 打印 prompt 摘要（最后一条 user message）
    - 记录 LLM 调用次数
    - 可以在这里实现缓存逻辑（返回 LlmResponse 跳过 LLM 调用）
    """
    ctx = callback_context

    # 提取最后一条用户消息
    last_user_msg = ""
    for content in reversed(llm_request.contents):
        if content.role == "user" and content.parts:
            last_user_msg = content.parts[0].text or ""
            break

    summary = last_user_msg[:80] + "..." if len(last_user_msg) > 80 else last_user_msg
    print(f"  [before_model] Sending to LLM: \"{summary}\"")

    # 累加 LLM 调用计数
    llm_calls = ctx.state.get("app:llm_call_count", 0) + 1
    ctx.state["app:llm_call_count"] = llm_calls

    # 返回 None → 继续调用 LLM
    # 返回 LlmResponse → 跳过 LLM 调用（缓存命中）
    return None


def after_model_callback(
    *, callback_context: CallbackContext, llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """LLM 调用后回调。

    - 打印 token 用量（如果有 usage_metadata）
    - 打印响应摘要
    """
    # Token 用量
    if llm_response.usage_metadata:
        usage = llm_response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", None) or 0
        output_tokens = getattr(usage, "candidates_token_count", None) or 0
        total_tokens = getattr(usage, "total_token_count", None) or 0
        print(f"  [after_model] Tokens: prompt={prompt_tokens}, output={output_tokens}, total={total_tokens}")
    else:
        print("  [after_model] No usage metadata available")

    # 响应摘要
    if llm_response.content and llm_response.content.parts:
        first_part = llm_response.content.parts[0]
        if hasattr(first_part, "text") and first_part.text:
            text = first_part.text
            summary = text[:60] + "..." if len(text) > 60 else text
            print(f"  [after_model] Response: \"{summary}\"")

    # 返回 None → 保持原始响应
    # 返回 LlmResponse → 替换原始响应
    return None


def on_model_error_callback(
    *, callback_context: CallbackContext, llm_request: LlmRequest, error: Exception,
) -> Optional[LlmResponse]:
    """LLM 调用出错时的降级回调。

    - 记录错误信息
    - 返回友好的降级响应（而不是抛异常）
    """
    print(f"  [on_model_error] LLM error: {type(error).__name__}: {error}")

    # 返回降级响应 → 抑制错误
    return LlmResponse(
        content=types.Content(
            parts=[types.Part.from_text(
                text="I'm sorry, I encountered a temporary issue. Please try again later."
            )],
            role="model",
        ),
    )
