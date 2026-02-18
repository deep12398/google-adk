"""State scoping 全演示。

使用单个 research_agent 展示四种 state scope：
  - user: scope（用户偏好，跨 session 持久化）
  - app: scope（全局计数器，所有用户共享）
  - session scope（会话笔记，仅本 session 可见）
  - temp: scope（临时暂存，永不持久化）

同时展示 event sourcing：通过 inspect_state_changes 看到完整的状态变更历史。
"""

from agents.research_agent import research_agent

state_demo_agent = research_agent
