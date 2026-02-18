"""摘要技能：纯 LLM 推理，无工具。

演示：Skill 不一定包含工具。有些技能只是一组操作指南，
LLM 凭自身能力就能执行，不需要外部工具。
"""

from skills.base import Skill
from prompts.templates import OUTPUT_FORMAT

summary_skill = Skill(
    name="summary",
    description=(
        "Condense and restructure text into concise summaries. "
        "Use when asked to summarize, condense, or create an executive brief."
    ),
    instruction=(
        "## Summary Skill Instructions\n\n"
        "When summarizing content:\n"
        "1. Identify the 3-5 most important points.\n"
        "2. Remove redundancy and filler.\n"
        "3. Preserve key data points, numbers, and conclusions.\n"
        "4. Structure output as:\n"
        "   - Executive Summary (2-3 sentences)\n"
        "   - Key Points (bullet list)\n"
        "   - Conclusion\n\n"
        f"{OUTPUT_FORMAT}"
    ),
    tools=[],  # 无工具——纯 LLM 推理
)
