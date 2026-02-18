"""带渐进加载的 skilled agent——单领域研究场景。

这个 agent 启动时不知道要用什么工具，只有技能目录。
LLM 根据用户请求选择技能 → 调用 activate_skill → 工具动态出现。

对比传统方式：
  传统: tools=[search_web, summarize_text, ...]  ← 全量注册，每次 LLM 调用都发送
  渐进: tools=[SkillAwareToolset]                 ← 按需加载，未激活的工具不发送
"""

from google.adk.agents.llm_agent import LlmAgent

from skills.base import SkillRegistry
from skills.loader import SkillAwareToolset, make_skill_instruction
from skills.research import research_skill
from skills.summary import summary_skill

registry = SkillRegistry([research_skill, summary_skill])

skilled_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="skilled_agent",
    description="Research assistant with progressive skill loading.",
    instruction=make_skill_instruction(registry),
    tools=[SkillAwareToolset(registry)],
    output_key="skilled_output",
)
