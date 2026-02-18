"""Memory + Artifact 联合演示。

SequentialAgent: researcher → report_writer
  - researcher 用 search_web 做研究，结果写入 session state
  - report_writer 先 search_memory 找历史上下文，再写报告并 save_artifact
  - 演示 memory 跨 session 搜索 + artifact 版本管理

注意：InMemoryMemoryService 需要先有 session 被添加到 memory 中才能搜索到。
首次运行时 search_memory 不会返回结果，这是正常的。
第二次运行（相同 user_id）时才能搜索到之前的对话。
"""

from google.adk.agents import SequentialAgent

from agents.research_agent import research_agent
from agents.report_agent import report_agent

memory_demo_agent = SequentialAgent(
    name="memory_demo",
    sub_agents=[research_agent, report_agent],
    description="Research then write a versioned report with memory recall.",
)
