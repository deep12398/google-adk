from google.adk.agents.llm_agent import LlmAgent


research_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="research_agent",
    description="Collects key points and sources for a topic.",
    instruction=(
        "Produce 4-6 bullet points of key facts and angles. "
        "Keep them concise."
    ),
    output_key="research_notes",
)
