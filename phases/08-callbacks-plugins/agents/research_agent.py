"""带回调 + GenerateContentConfig 的研究 Agent。

演示：
  1. Agent 级 9 种回调的挂载方式
  2. GenerateContentConfig 调参（temperature / max_output_tokens）
  3. 回调签名和返回值的作用
"""

from google.genai import types

from google.adk.agents import LlmAgent

from callbacks.agent_callbacks import before_agent_callback, after_agent_callback
from callbacks.model_callbacks import (
    before_model_callback,
    after_model_callback,
    on_model_error_callback,
)
from callbacks.tool_callbacks import (
    before_tool_callback,
    after_tool_callback,
    on_tool_error_callback,
)
from tools.search_tool import search_web_tool


def create_research_agent(
    temperature: float = 0.3,
    max_output_tokens: int = 500,
    with_callbacks: bool = True,
) -> LlmAgent:
    """创建带回调和配置的研究 Agent。

    Args:
        temperature: LLM 采样温度（0=确定性，2=高随机性）。
        max_output_tokens: 最大输出 token 数。
        with_callbacks: 是否挂载回调函数。
    """
    kwargs = dict(
        model="gemini-2.0-flash",
        name="research_agent",
        description="A research agent that searches the web and summarizes findings.",
        instruction=(
            "You are a research assistant. When the user asks about a topic:\n"
            "1. Use search_web to find relevant information\n"
            "2. Summarize the findings concisely\n"
            "Be factual and cite the sources from search results."
        ),
        tools=[search_web_tool],
        generate_content_config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )

    # Error callbacks are always enabled (defensive, not monitoring)
    kwargs.update(
        on_model_error_callback=on_model_error_callback,
        on_tool_error_callback=on_tool_error_callback,
    )

    if with_callbacks:
        kwargs.update(
            before_agent_callback=before_agent_callback,
            after_agent_callback=after_agent_callback,
            before_model_callback=before_model_callback,
            after_model_callback=after_model_callback,
            before_tool_callback=before_tool_callback,
            after_tool_callback=after_tool_callback,
        )

    return LlmAgent(**kwargs)
