"""采购操作审计插件——记录所有搜索和报价操作。

与 LoggingPlugin 不同：
  - LoggingPlugin 记录所有事件（Agent/Model/Tool）
  - AuditTrailPlugin 只关注采购操作（search, quote）
  - 收集结构化审计记录，可输出为报告
"""

import datetime
from typing import Any, Optional

from google.adk.agents.invocation_context import InvocationContext
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# 需要审计的工具名称
AUDITABLE_TOOLS = {
    "search_catalog", "search_suppliers", "search_external",
    "generate_quote", "collect_requirements",
}


class AuditTrailPlugin(BasePlugin):
    """采购操作审计插件——记录关键操作供合规审查。"""

    def __init__(self) -> None:
        super().__init__(name="audit_trail")
        self._operations: list[dict] = []

    async def before_tool_callback(
        self, *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        if tool.name in AUDITABLE_TOOLS:
            self._operations.append({
                "tool": tool.name,
                "args": {k: str(v)[:100] for k, v in tool_args.items()},
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "phase": "before",
            })
        return None

    async def after_run_callback(
        self, *, invocation_context: InvocationContext,
    ) -> None:
        print(f"\n  [audit_trail] === Audit Summary ===")
        print(f"  [audit_trail] {len(self._operations)} sourcing operations recorded:")
        for op in self._operations:
            print(f"  [audit_trail]   {op['timestamp']} | {op['tool']} | {op['args']}")

    @property
    def operations(self) -> list[dict]:
        """返回审计记录（供测试使用）。"""
        return list(self._operations)

    def reset(self) -> None:
        """重置审计记录。"""
        self._operations.clear()
