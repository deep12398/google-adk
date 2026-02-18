"""成本追踪插件——统计 LLM 调用次数和 token 用量。

演示 Plugin 的状态收集能力：
  - after_model_callback：每次 LLM 调用后累加 token 计数
  - after_run_callback：打印成本摘要
"""

from typing import Any, Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin


class CostTrackerPlugin(BasePlugin):
    """成本追踪插件——统计 token 用量。"""

    def __init__(self) -> None:
        super().__init__(name="cost_tracker")
        self._llm_calls = 0
        self._prompt_tokens = 0
        self._output_tokens = 0
        self._total_tokens = 0

    @property
    def llm_calls(self) -> int:
        return self._llm_calls

    @property
    def prompt_tokens(self) -> int:
        return self._prompt_tokens

    @property
    def output_tokens(self) -> int:
        return self._output_tokens

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    def get_summary(self) -> dict:
        """返回成本摘要字典。"""
        return {
            "llm_calls": self._llm_calls,
            "prompt_tokens": self._prompt_tokens,
            "output_tokens": self._output_tokens,
            "total_tokens": self._total_tokens,
        }

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        """每次 LLM 调用后累加 token 计数。"""
        self._llm_calls += 1

        if llm_response.usage_metadata:
            usage = llm_response.usage_metadata
            self._prompt_tokens += getattr(usage, "prompt_token_count", None) or 0
            self._output_tokens += getattr(usage, "candidates_token_count", None) or 0
            self._total_tokens += getattr(usage, "total_token_count", None) or 0

        return None  # 不修改响应

    async def after_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> None:
        """Runner 结束后打印成本摘要。"""
        print(f"\n  [cost_tracker] === Cost Summary ===")
        print(f"  [cost_tracker] LLM calls:     {self._llm_calls}")
        print(f"  [cost_tracker] Prompt tokens:  {self._prompt_tokens}")
        print(f"  [cost_tracker] Output tokens:  {self._output_tokens}")
        print(f"  [cost_tracker] Total tokens:   {self._total_tokens}")

    def reset(self) -> None:
        """重置计数器（用于测试）。"""
        self._llm_calls = 0
        self._prompt_tokens = 0
        self._output_tokens = 0
        self._total_tokens = 0
