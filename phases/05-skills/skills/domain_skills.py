"""领域研究技能：科技 / 市场 / 法规。

三个 Skill 共享同一个 search_web 工具，但 instruction 各自聚焦不同领域。
演示：同一个工具被多个 Skill 包含时，SkillAwareToolset 会自动去重。
"""

from skills.base import Skill
from tools.search_tool import search_web
from prompts.templates import OUTPUT_FORMAT

tech_skill = Skill(
    name="tech_research",
    description="Research technology topics: AI, cloud, semiconductors, etc.",
    instruction=(
        "## Technology Research Instructions\n\n"
        "Focus on:\n"
        "- AI & machine learning advances\n"
        "- Cloud infrastructure trends\n"
        "- Semiconductor developments\n\n"
        "Search for recent papers, product launches, and expert opinions.\n\n"
        f"{OUTPUT_FORMAT}"
    ),
    tools=[search_web],
)

market_skill = Skill(
    name="market_research",
    description=(
        "Research market topics: market size, competition, investment trends."
    ),
    instruction=(
        "## Market Research Instructions\n\n"
        "Focus on:\n"
        "- Market size & growth projections\n"
        "- Competitive landscape analysis\n"
        "- Investment and funding trends\n\n"
        "Search for industry reports, financial data, and analyst opinions.\n\n"
        f"{OUTPUT_FORMAT}"
    ),
    tools=[search_web],
)

legal_skill = Skill(
    name="legal_research",
    description=(
        "Research legal & regulatory topics: compliance, policy, risk."
    ),
    instruction=(
        "## Legal & Regulatory Research Instructions\n\n"
        "Focus on:\n"
        "- Compliance requirements and standards\n"
        "- Recent policy changes and proposals\n"
        "- Regulatory risk assessment\n\n"
        "Search for official regulations, legal analyses, and policy briefs.\n\n"
        f"{OUTPUT_FORMAT}"
    ),
    tools=[search_web],
)
