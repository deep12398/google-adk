"""Skill 基础定义 + 注册中心。

Skill（技能包）= 一组可按需加载的能力，包含三层：
  - 元数据层 (name + description): 始终可见，帮助 LLM 判断何时使用 (~100 tokens)
  - 指令层 (instruction): 完整操作指南，激活后才加载
  - 工具层 (tools): 关联的工具函数，激活后才注册到 LLM 请求

复用自 Phase 05。
"""

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Skill:
    """技能包：可复用的能力单元。"""

    name: str
    description: str
    instruction: str
    tools: list[Callable] = field(default_factory=list)


class SkillRegistry:
    """技能注册中心：管理技能的发现、目录生成与按需检索。"""

    def __init__(self, skills: list[Skill]):
        self._skills = {s.name: s for s in skills}

    def get_catalog(self) -> str:
        """生成技能目录文本（元数据层）——只有 name + description。"""
        lines = []
        for s in self._skills.values():
            lines.append(f"- **{s.name}**: {s.description}")
        return "\n".join(lines)

    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def has_skill(self, name: str) -> bool:
        return name in self._skills

    def list_names(self) -> list[str]:
        return list(self._skills.keys())

    def get_active_instruction(self, active_names: list[str]) -> str:
        """拼接已激活技能的完整指令。"""
        parts = []
        for name in active_names:
            skill = self._skills.get(name)
            if skill:
                parts.append(skill.instruction)
        return "\n\n".join(parts)

    def get_active_tools(self, active_names: list[str]) -> list[Callable]:
        """收集已激活技能的工具函数（去重）。"""
        seen = set()
        tools = []
        for name in active_names:
            skill = self._skills.get(name)
            if skill:
                for t in skill.tools:
                    if t.__name__ not in seen:
                        seen.add(t.__name__)
                        tools.append(t)
        return tools
