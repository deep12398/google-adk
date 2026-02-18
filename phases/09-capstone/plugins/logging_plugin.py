"""全局日志插件——记录所有 Agent/Model/Tool 事件流。

继承 BasePlugin，实现所有回调方法。
注册到 App(plugins=[LoggingPlugin()]) 后，对所有 Agent 生效。

Plugin vs Callback 执行顺序：
  Plugin.before_xxx → Agent.before_xxx_callback → 执行 → Agent.after_xxx_callback → Plugin.after_xxx
  Plugin 先执行，如果返回非 None → 跳过后续 Agent callback
"""

from typing import Any, Optional

from google.genai import types

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


class LoggingPlugin(BasePlugin):
    """全局日志插件——打印所有事件的时间线。"""

    def __init__(self) -> None:
        super().__init__(name="logging")
        self._event_count = 0

    def _log(self, tag: str, msg: str) -> None:
        self._event_count += 1
        print(f"  [{self.name}#{self._event_count:03d}] {tag}: {msg}")

    # --- Lifecycle hooks ---

    async def before_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> Optional[types.Content]:
        self._log("LIFECYCLE", "Runner starting")
        return None

    async def after_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> None:
        self._log("LIFECYCLE", f"Runner finished (total events: {self._event_count})")

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Optional[Event]:
        author = getattr(event, "author", "unknown")
        self._log("EVENT", f"Event from '{author}'")
        return None

    # --- Agent hooks ---

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        self._log("AGENT", f"Agent '{agent.name}' starting")
        return None

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        self._log("AGENT", f"Agent '{agent.name}' finished")
        return None

    # --- Model hooks ---

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        num_contents = len(llm_request.contents)
        self._log("MODEL", f"Sending to LLM ({num_contents} messages)")
        return None

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        if llm_response.usage_metadata:
            usage = llm_response.usage_metadata
            total = getattr(usage, "total_token_count", None) or 0
            self._log("MODEL", f"LLM responded (total_tokens={total})")
        else:
            self._log("MODEL", "LLM responded (no usage metadata)")
        return None

    async def on_model_error_callback(
        self, *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
        error: Exception,
    ) -> Optional[LlmResponse]:
        self._log("MODEL", f"LLM error: {type(error).__name__}: {error}")
        return None

    # --- Tool hooks ---

    async def before_tool_callback(
        self, *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        self._log("TOOL", f"Calling '{tool.name}' with {tool_args}")
        return None

    async def after_tool_callback(
        self, *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        result_str = str(result)
        summary = result_str[:80] + "..." if len(result_str) > 80 else result_str
        self._log("TOOL", f"'{tool.name}' returned: {summary}")
        return None

    async def on_tool_error_callback(
        self, *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> Optional[dict]:
        self._log("TOOL", f"'{tool.name}' error: {type(error).__name__}: {error}")
        return None
