# Step 8: 插件 + 配置优化

## 教学目标

- **Phase 08** BasePlugin 子类 + App(plugins=[...])
- **Phase 08** GenerateContentConfig 温度/token 配置

## 学到什么

Plugin 如何全局生效（无需修改每个 Agent 代码），
与 callback 的执行顺序关系（Plugin 先执行），
以及如何通过 GenerateContentConfig 为不同 Agent 调优参数。

## 核心概念

```
BasePlugin    — 插件基类，实现与 callback 相同的方法（但全局生效）
App(plugins=) — 插件注册到 App 上，对所有 Agent 生效
Plugin 执行顺序：
  Plugin.before_xxx → Agent.before_xxx_callback → 执行 → Agent.after_xxx_callback → Plugin.after_xxx

GenerateContentConfig — 控制 LLM 行为（temperature, max_output_tokens, top_p 等）
  - orchestrator: temperature=0.1 → 确定性路由
  - qa_agent: temperature=0.3 → 适度创造性分析
  - quote_agent: temperature=0.0 → 精确报价
```

## 创建文件清单

```
新建:
  plugins/
    __init__.py
    logging_plugin.py         # 全局事件日志（复用 Phase 08 模式）
    cost_tracker_plugin.py    # Token 统计（复用 Phase 08 模式）
    audit_trail_plugin.py     # NEW：采购操作审计

修改:
  apps/app.py                 # App(plugins=[...]) + STEP="8"
  agents/orchestrator.py      # GenerateContentConfig(temperature=0.1)
  agents/qa_agent.py          # GenerateContentConfig(temperature=0.3)
  agents/quote_agent.py       # GenerateContentConfig(temperature=0.0)
```

## 代码实现

### plugins/logging_plugin.py

直接复用 Phase 08 的 `LoggingPlugin`（`phases/08-callbacks-plugins/plugins/logging_plugin.py`）。
只需复制文件，无需修改。

### plugins/cost_tracker_plugin.py

直接复用 Phase 08 的 `CostTrackerPlugin`（`phases/08-callbacks-plugins/plugins/cost_tracker_plugin.py`）。
只需复制文件，无需修改。

### plugins/audit_trail_plugin.py

```python
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
```

### apps/app.py（Step 8 修改）

```python
# Step 8: 带 Plugin 的 App
if STEP >= 8:
    from plugins.logging_plugin import LoggingPlugin
    from plugins.cost_tracker_plugin import CostTrackerPlugin
    from plugins.audit_trail_plugin import AuditTrailPlugin

    app = App(
        name=f"sourcing_step{STEP}",
        root_agent=root_agent,
        plugins=[LoggingPlugin(), CostTrackerPlugin(), AuditTrailPlugin()],
    )
```

### GenerateContentConfig 修改

```python
# agents/orchestrator.py
from google.genai import types

sourcing_orchestrator = LlmAgent(
    ...,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,  # 确定性路由
    ),
)

# agents/qa_agent.py
qa_agent = LlmAgent(
    ...,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,  # 适度创造性
    ),
)

# agents/quote_agent.py
quote_agent = LlmAgent(
    ...,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,        # 精确报价
        max_output_tokens=1000,  # 报价需要详细输出
    ),
)
```

## Plugin vs Callback 对比

| 维度 | Callback | Plugin |
|------|----------|--------|
| 注册位置 | Agent 参数 | App(plugins=) |
| 作用范围 | 单个 Agent | 全局所有 Agent |
| 执行顺序 | 后执行 | 先执行 |
| 拦截能力 | 返回非 None 可拦截 | 返回非 None 可拦截（且跳过 callback）|
| 生命周期 | 无 | 有 before_run / after_run / on_event |
| 适用场景 | Agent 特定逻辑 | 横切关注点（日志、审计、限流）|

## 验证

```bash
cd phases/09-capstone
STEP=8 PROMPT="Find steel sheets and get a quote for 100 tons" python apps/main.py
```

**期望输出：**
```
  [logging#001] LIFECYCLE: Runner starting
  [logging#002] AGENT: Agent 'sourcing_orchestrator' starting
  [logging#003] MODEL: Sending to LLM (1 messages)
  [logging#004] MODEL: LLM responded (total_tokens=312)
  [logging#005] TOOL: Calling 'classify_intent' with {...}
  ...
  [audit_trail] === Audit Summary ===
  [audit_trail] 3 sourcing operations recorded:
  [audit_trail]   2025-01-15T10:30:00Z | search_catalog | {'query': 'steel sheets'}
  [audit_trail]   2025-01-15T10:30:02Z | collect_requirements | {'product_description': '...'}
  [audit_trail]   2025-01-15T10:30:05Z | generate_quote | {'product_id': 'P001', ...}

  [cost_tracker] === Cost Summary ===
  [cost_tracker] LLM calls:     8
  [cost_tracker] Total tokens:   2456
```

## 你应该理解的

1. Plugin 注册到 `App(plugins=[])` → 全局生效，无需改 Agent 代码
2. Plugin 先于 callback 执行 → 可作为全局守卫
3. `LoggingPlugin` 和 `CostTrackerPlugin` 是可复用的基础设施
4. `AuditTrailPlugin` 是业务特有的 → 只审计采购操作
5. `GenerateContentConfig` 按 Agent 角色调优 → orchestrator 低温度，qa 适度，quote 零温度
6. Plugin 有 `before_run_callback` / `after_run_callback` → 生命周期钩子
