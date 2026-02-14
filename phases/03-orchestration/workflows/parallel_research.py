from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.parallel_agent import ParallelAgent


market_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="market_agent",
    description="Researches market context.",
    instruction="List 3-5 market context points about the topic.",
    output_key="market_notes",
)

tech_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="tech_agent",
    description="Researches technical aspects.",
    instruction="List 3-5 technical points about the topic.",
    output_key="tech_notes",
)

risk_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="risk_agent",
    description="Researches risks and open questions.",
    instruction="List 3-5 risks or open questions about the topic.",
    output_key="risk_notes",
)

parallel_agent = ParallelAgent(
    name="parallel_research",
    description="Runs market/tech/risk research in parallel.",
    sub_agents=[market_agent, tech_agent, risk_agent],
)
