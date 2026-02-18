"""共享 prompt 片段——跨 Skill 复用的文本常量。

多个 Skill 的 instruction 都需要输出格式、研究规范等约定，
把它们抽成常量，避免在每个 Skill 定义里重复写。
"""

OUTPUT_FORMAT = (
    "## Output Format\n"
    "- Use bullet points for key findings.\n"
    "- Assess the reliability of each finding (high / medium / low).\n"
    "- End with a 2-3 sentence summary.\n"
)

RESEARCH_GUIDELINES = (
    "## Research Guidelines\n"
    "- Use search_web to gather information (2-3 queries recommended).\n"
    "- Use summarize_text if a source is too long.\n"
    "- Cross-reference multiple sources when possible.\n"
)

REPORT_STRUCTURE = (
    "## Report Structure\n"
    "1. Executive Summary (2-3 sentences)\n"
    "2. Key Findings (bullet points per domain)\n"
    "3. Cross-Domain Insights\n"
    "4. Recommendations\n"
)

# ---------------------------------------------------------------------------
# 字符串模板——用于 include_contents="none" 的汇总 agent
# ADK 自动把 {state_key} 替换为 session.state 中的值
# ---------------------------------------------------------------------------

REPORT_INSTRUCTION = (
    "You are a report synthesizer. You do NOT have access to the conversation "
    "history — only the structured research findings below.\n\n"
    "## Technology Research\n{tech_researcher_notes}\n\n"
    "## Market Research\n{market_researcher_notes}\n\n"
    "## Legal Research\n{legal_researcher_notes}\n\n"
    f"{REPORT_STRUCTURE}\n"
    "Synthesize the above findings into a cohesive executive report. "
    "Highlight connections and tensions between domains."
)
