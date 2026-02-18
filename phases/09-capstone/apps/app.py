"""Phase 09 App 定义——STEP 路由模式。

通过 STEP 环境变量选择不同的 root_agent：
  STEP=1 → catalog_search_agent（单 Agent 搜索）
  STEP=2-7 → sourcing_orchestrator（多 Agent 协调）
  STEP=8+ → sourcing_orchestrator + 3 个全局 Plugin

这个文件会随着每个 Step 增量修改。
"""

import os
import sys
from pathlib import Path

from google.adk.apps import App

# --- sys.path 设置（Phase 02 约定）---
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- Agent 导入 ---
from agents.catalog_search_agent import catalog_search_agent  # noqa: E402
from agents.orchestrator import sourcing_orchestrator  # noqa: E402

# --- STEP 路由 ---
STEP = os.getenv("STEP", "1")

ROOT_AGENTS = {
    "1": catalog_search_agent,
    "2": sourcing_orchestrator,
    "3": sourcing_orchestrator,
    "4": sourcing_orchestrator,
    "5": sourcing_orchestrator,
    "6": sourcing_orchestrator,
    "7": sourcing_orchestrator,
    "8": sourcing_orchestrator,
    "9": sourcing_orchestrator,
}

root_agent = ROOT_AGENTS.get(STEP, catalog_search_agent)

# --- Step 8+: 全局 Plugin ---
if int(STEP) >= 8:
    from plugins.audit_trail_plugin import AuditTrailPlugin  # noqa: E402
    from plugins.cost_tracker_plugin import CostTrackerPlugin  # noqa: E402
    from plugins.logging_plugin import LoggingPlugin  # noqa: E402

    app = App(
        name=f"sourcing_step{STEP}",
        root_agent=root_agent,
        plugins=[LoggingPlugin(), CostTrackerPlugin(), AuditTrailPlugin()],
    )
else:
    app = App(
        name=f"sourcing_step{STEP}",
        root_agent=root_agent,
    )
