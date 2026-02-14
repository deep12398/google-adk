from google.adk.agents.llm_agent import LlmAgent

from tools.basic_tools import say_hello


greeting_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="greeting_agent",
    description="Handles greetings and welcomes.",
    instruction=(
        "If the user greets, call say_hello. "
        "Keep responses short and friendly."
    ),
    tools=[say_hello],
)
