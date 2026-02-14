from google.adk.agents.llm_agent import LlmAgent

from tools.basic_tools import say_goodbye


farewell_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="farewell_agent",
    description="Handles goodbyes and closings.",
    instruction=(
        "If the user says goodbye, call say_goodbye. "
        "Keep responses short and friendly."
    ),
    tools=[say_goodbye],
)
