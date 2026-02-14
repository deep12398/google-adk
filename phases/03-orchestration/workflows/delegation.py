from google.adk.agents.llm_agent import LlmAgent

from agents.farewell_agent import farewell_agent
from agents.greeting_agent import greeting_agent
from tools.basic_tools import get_weather


delegation_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="delegation_root",
    description="Delegates greetings/closings to sub-agents and handles weather.",
    instruction=(
        "You are the coordinator. "
        "Delegate greetings to the greeting agent and goodbyes to the farewell agent. "
        "For weather questions, call get_weather. "
        "Otherwise answer directly."
    ),
    tools=[get_weather],
    sub_agents=[greeting_agent, farewell_agent],
)
