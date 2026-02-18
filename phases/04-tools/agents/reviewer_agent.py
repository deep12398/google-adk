from google.adk.agents.llm_agent import LlmAgent


reviewer_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="reviewer_agent",
    description="Reviews a report for accuracy, clarity, and completeness.",
    instruction=(
        "You are a quality reviewer. Evaluate the provided content for:\n"
        "- Factual accuracy\n"
        "- Logical structure\n"
        "- Clarity and completeness\n\n"
        "Provide a score (1-10) and specific improvement suggestions."
    ),
)
