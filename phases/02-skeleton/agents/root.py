from google.adk.agents.llm_agent import Agent


root_agent = Agent(
    model="gemini-2.5-flash",
    name="skeleton_root",
    description="Empty root agent for skeleton stage.",
    instruction="A placeholder root agent for the skeleton phase.",
)
