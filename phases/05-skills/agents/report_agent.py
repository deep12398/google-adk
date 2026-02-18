"""报告整合 Agent —— 演示 include_contents="none" 上下文隔离。

include_contents="none" 的效果：
- Agent 不收到对话历史（前几轮的 user/assistant 消息）
- 只能通过 instruction 中的 {state_key} 模板读取 state
- 适用于"汇总"角色：只需要结构化数据，不需要对话过程
"""

from google.adk.agents.llm_agent import LlmAgent

from prompts.templates import REPORT_INSTRUCTION

report_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="report_agent",
    description="Synthesizes multi-domain research into a unified executive report.",
    instruction=REPORT_INSTRUCTION,
    include_contents="none",
    output_key="final_report",
)
