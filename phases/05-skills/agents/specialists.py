"""领域研究员：apply_skill() vs clone() 两种创建方式。

apply_skill() 把 Skill 知识包"装载"到 Agent 上——
Skill 是独立的数据对象，Agent 是运行载体，两者解耦。

clone() 从已有 Agent 派生变体——适合只改几个字段的场景。
"""

from google.adk.agents.llm_agent import LlmAgent

from skills.base import Skill
from skills.domain_skills import tech_skill, market_skill, legal_skill


def apply_skill(
    skill: Skill,
    name: str,
    output_key: str | None = None,
    model: str = "gemini-2.5-flash",
) -> LlmAgent:
    """把技能包装载到一个新 Agent 上。

    不是"Agent 工厂"——Skill 是独立存在的知识包，
    apply_skill 只是把它挂载到 Agent 这个运行载体上。
    """
    return LlmAgent(
        model=model,
        name=name,
        description=skill.description,
        instruction=skill.instruction,
        tools=skill.tools,
        output_key=output_key or f"{name}_notes",
    )


# ====================================================================
# 方式 1: apply_skill —— 从技能包创建 Agent
# ====================================================================

tech_researcher = apply_skill(tech_skill, "tech_researcher")
market_researcher = apply_skill(market_skill, "market_researcher")
legal_researcher = apply_skill(legal_skill, "legal_researcher")


# ====================================================================
# 方式 2: clone() —— 从基础 Agent 派生变体
# ====================================================================

_base = apply_skill(tech_skill, "base_researcher")

market_researcher_v2 = _base.clone(
    update={
        "name": "market_researcher_v2",
        "description": market_skill.description,
        "instruction": market_skill.instruction,
        "output_key": "market_researcher_v2_notes",
    }
)

legal_researcher_v2 = _base.clone(
    update={
        "name": "legal_researcher_v2",
        "description": legal_skill.description,
        "instruction": legal_skill.instruction,
        "output_key": "legal_researcher_v2_notes",
    }
)
