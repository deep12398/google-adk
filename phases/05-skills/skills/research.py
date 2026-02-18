"""通用研究技能：搜索 + 摘要 + 综合分析。"""

from skills.base import Skill
from tools.search_tool import search_web, summarize_text
from prompts.templates import RESEARCH_GUIDELINES, OUTPUT_FORMAT

research_skill = Skill(
    name="research",
    description=(
        "Search the web and synthesize findings on any topic. "
        "Use when asked to research, investigate, or find information."
    ),
    instruction=(
        "## Research Skill Instructions\n\n"
        "When researching a topic:\n"
        "1. Use search_web with 2-3 different queries for diverse sources.\n"
        "2. Use summarize_text if any source is too lengthy.\n"
        "3. Synthesize findings into structured bullet points.\n"
        "4. Assess reliability of each finding (high / medium / low).\n"
        "5. End with a 2-3 sentence summary.\n\n"
        f"{RESEARCH_GUIDELINES}\n"
        f"{OUTPUT_FORMAT}"
    ),
    tools=[search_web, summarize_text],
)
