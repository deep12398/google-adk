"""Agent 定义入口——供 Runner 和其他模块导入。

提供两种配置：
  - root_agent：带所有回调的研究 Agent
  - create_app()：带全局插件的 App 实例
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from google.adk.apps.app import App

from agents.research_agent import create_research_agent
from plugins.logging_plugin import LoggingPlugin
from plugins.guard_plugin import GuardPlugin
from plugins.cost_tracker_plugin import CostTrackerPlugin


# --- 带回调的 Agent（DEMO=callbacks 模式使用）---
root_agent = create_research_agent(with_callbacks=True)

# --- 不带回调的 Agent（DEMO=plugins 模式使用，避免和 Plugin 日志混在一起）---
bare_agent = create_research_agent(with_callbacks=False)


def create_app(
    blocked_words: list[str] | None = None,
) -> tuple[App, LoggingPlugin, GuardPlugin, CostTrackerPlugin]:
    """创建带全局插件的 App 实例。

    返回 (app, logging_plugin, guard_plugin, cost_tracker_plugin)
    以便外部读取 Plugin 状态。
    """
    logging_plugin = LoggingPlugin()
    guard_plugin = GuardPlugin(blocked_words=blocked_words or ["hack", "exploit"])
    cost_tracker_plugin = CostTrackerPlugin()

    app = App(
        name="research_app",
        root_agent=bare_agent,
        plugins=[logging_plugin, guard_plugin, cost_tracker_plugin],
    )

    return app, logging_plugin, guard_plugin, cost_tracker_plugin
