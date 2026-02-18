from google.adk.agents.llm_agent import LlmAgent

from tools.file_tool import save_report_draft


writer_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="writer_agent",
    description="Writes structured reports and saves them as artifacts.",
    instruction=(
        "Using the research notes below, write a structured report with:\n"
        "1) Executive Summary\n"
        "2) Key Findings\n"
        "3) Open Questions\n\n"
        "After writing, call save_report_draft to persist the report.\n\n"
        "Research Notes:\n{research_notes}"
    ),
    tools=[save_report_draft],
    output_key="draft_report",
)
