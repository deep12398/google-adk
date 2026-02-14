from google.adk.agents.llm_agent import LlmAgent


write_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="write_agent",
    description="Drafts a short structured report from research notes.",
    instruction=(
        "Using the research notes below, write a short report with:\n"
        "1) Summary\n2) Key Points\n3) Open Questions\n\n"
        "Research Notes:\n{research_notes}"
    ),
    output_key="draft_report",
)
