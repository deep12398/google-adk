"""需求收集 Agent——品类推断 + 技能加载。

使用 SkillAwareToolset 实现渐进加载：
  1. LLM 首先看到技能目录（仅 name + description）
  2. 推断品类后调用 activate_skill → 加载完整指令
  3. 后续 LLM 请求自动获得领域专业知识
"""

from google.adk.agents.llm_agent import LlmAgent

from skills.base import SkillRegistry
from skills.electronics_skill import electronics_skill
from skills.loader import SkillAwareToolset, make_skill_instruction
from skills.packaging_skill import packaging_skill
from skills.steel_skill import steel_skill
from tools.requirement_tools import collect_requirements, infer_category

# 注册所有品类技能
registry = SkillRegistry([steel_skill, electronics_skill, packaging_skill])

requirements_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="requirements_agent",
    description="Collects sourcing requirements, infers category, loads domain expertise.",
    instruction=make_skill_instruction(registry),
    tools=[infer_category, collect_requirements, SkillAwareToolset(registry)],
    output_key="requirements_summary",
)
