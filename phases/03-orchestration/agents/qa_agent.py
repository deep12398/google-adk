from google.adk.agents.llm_agent import LlmAgent


qa_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="qa_agent",
    description="Checks draft quality and improves clarity.",
    instruction=(
        "Review the draft for clarity and logical issues. "
        "If needed, improve the draft.\n\n"
        "Draft:\n{draft_report}"
    ),
    output_key="final_report",
)
