from google.adk.agents.llm_agent import Agent
from google.adk.apps import App


def remember_topic(topic: str, tool_context) -> dict:
    """Store a temporary topic for this invocation in session state."""
    tool_context.state["temp:topic"] = topic
    return {"topic": topic}


root_agent = Agent(
    model="gemini-2.5-flash",
    name="concept_agent",
    description="Demonstrates ADK's four-layer model.",
    instruction=(
        "You are a concise assistant. "
        "When a user mentions a topic, call remember_topic. "
        "Use tools for actions and keep answers short."
    ),
    tools=[remember_topic],
)

app = App(
    name="concept_app",
    root_agent=root_agent,
)
