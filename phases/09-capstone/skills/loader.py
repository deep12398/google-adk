"""技能加载器：SkillAwareToolset + InstructionProvider。

实现渐进加载的两个核心组件：

1. SkillAwareToolset (BaseToolset 子类)
   - 未激活时：只暴露 activate_skill 元工具
   - 激活后：动态追加该技能的工具到 LLM 请求

2. make_skill_instruction (InstructionProvider 工厂)
   - 未激活时：只展示技能目录（元数据层）
   - 激活后：注入完整技能指令（指令层）

复用自 Phase 05，base prompt 改为采购场景。
"""

from google.adk.tools import FunctionTool, ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from skills.base import SkillRegistry


class SkillAwareToolset(BaseToolset):
    """渐进加载工具集：根据 state['active_skills'] 动态返回工具。"""

    def __init__(self, registry: SkillRegistry, **kwargs):
        super().__init__(**kwargs)
        self._registry = registry
        self._activate_tool = FunctionTool(self._build_activate_fn())
        self._tool_cache: dict[str, FunctionTool] = {}

    def _build_activate_fn(self):
        registry = self._registry

        def activate_skill(
            skill_name: str, tool_context: ToolContext = None
        ) -> dict:
            """Activate a skill to gain access to its specialized tools and instructions.

            Args:
                skill_name: The name of the skill to activate.
            """
            if not registry.has_skill(skill_name):
                return {
                    "error": f"Unknown skill: '{skill_name}'",
                    "available_skills": registry.list_names(),
                }
            active = list(tool_context.state.get("active_skills", []))
            if skill_name not in active:
                active.append(skill_name)
                tool_context.state["active_skills"] = active
            skill = registry.get_skill(skill_name)
            return {
                "status": "activated",
                "skill": skill_name,
                "tools_now_available": (
                    [t.__name__ for t in skill.tools]
                    if skill.tools
                    else ["(none — this skill uses LLM reasoning only)"]
                ),
            }

        return activate_skill

    async def get_tools(self, readonly_context=None) -> list[BaseTool]:
        """每次 LLM 调用前被 ADK 调用。只返回已激活技能的工具。"""
        tools: list[BaseTool] = [self._activate_tool]
        if readonly_context:
            active = readonly_context.state.get("active_skills", [])
            for name in active:
                skill = self._registry.get_skill(name)
                if skill:
                    for fn in skill.tools:
                        key = fn.__name__
                        if key not in self._tool_cache:
                            self._tool_cache[key] = FunctionTool(fn)
                        tools.append(self._tool_cache[key])
        return tools


def make_skill_instruction(registry: SkillRegistry):
    """创建 InstructionProvider：根据激活状态动态生成 system instruction。"""
    catalog = registry.get_catalog()

    def provider(ctx) -> str:
        active = ctx.state.get("active_skills", [])

        base = (
            "You are a sourcing requirements specialist with a skill-based architecture.\n\n"
            "## Available Category Skills\n"
            f"{catalog}\n\n"
        )

        if not active:
            return base + (
                "**No skills are currently active.**\n"
                "1. First use `infer_category` to determine the product category.\n"
                "2. Then call `activate_skill` with the matching category name.\n"
                "3. Use `collect_requirements` to gather structured requirements.\n"
            )

        skill_instructions = registry.get_active_instruction(active)
        return base + (
            f"**Active skills:** {', '.join(active)}\n\n"
            f"{skill_instructions}\n\n"
            "Now use your domain expertise to help the user.\n"
            "Each skill above has an 'Adapt to User's Expertise Level' section — follow it.\n"
            "After the conversation, use `collect_requirements` to structure everything "
            "into state for downstream agents.\n"
        )

    return provider
