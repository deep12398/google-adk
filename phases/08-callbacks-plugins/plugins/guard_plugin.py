"""内容安全插件——拦截包含敏感词的输入和输出。

演示 Plugin 的拦截能力：
  - before_model_callback：检查用户输入，包含敏感词则跳过 LLM 调用
  - after_model_callback：检查 LLM 输出，包含敏感词则替换响应

当 Plugin 返回非 None 时，会跳过后续的 Agent callback。
"""

from typing import Any, Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin


class GuardPlugin(BasePlugin):
    """内容安全插件——拦截敏感词。"""

    def __init__(
        self,
        blocked_words: list[str] | None = None,
    ) -> None:
        super().__init__(name="guard")
        self._blocked_words = [w.lower() for w in (blocked_words or ["hack", "exploit"])]
        self._blocked_count = 0

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    def _contains_blocked(self, text: str) -> str | None:
        """检查文本是否包含敏感词，返回命中的词或 None。"""
        text_lower = text.lower()
        for word in self._blocked_words:
            if word in text_lower:
                return word
        return None

    def _extract_text(self, content: types.Content | None) -> str:
        """从 Content 中提取所有文本。"""
        if not content or not content.parts:
            return ""
        return " ".join(
            part.text for part in content.parts
            if hasattr(part, "text") and part.text
        )

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        """检查用户输入——包含敏感词则跳过 LLM 调用。"""
        for content in llm_request.contents:
            if content.role != "user":
                continue
            text = self._extract_text(content)
            hit = self._contains_blocked(text)
            if hit:
                self._blocked_count += 1
                print(f"  [guard] BLOCKED input (word='{hit}'): \"{text[:60]}...\"")
                return LlmResponse(
                    content=types.Content(
                        parts=[types.Part.from_text(
                            text=f"I'm sorry, I cannot process this request. "
                                 f"Your input contains restricted content."
                        )],
                        role="model",
                    ),
                )
        return None

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        """检查 LLM 输出——包含敏感词则替换响应。"""
        text = self._extract_text(llm_response.content)
        hit = self._contains_blocked(text)
        if hit:
            self._blocked_count += 1
            print(f"  [guard] BLOCKED output (word='{hit}')")
            return LlmResponse(
                content=types.Content(
                    parts=[types.Part.from_text(
                        text="I've generated a response, but it was filtered "
                             "due to content policy restrictions."
                    )],
                    role="model",
                ),
                usage_metadata=llm_response.usage_metadata,
            )
        return None
