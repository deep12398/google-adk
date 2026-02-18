from google.adk.agents.sequential_agent import SequentialAgent

from agents.research_agent import research_agent
from agents.writer_agent import writer_agent


pipeline_agent = SequentialAgent(
    name="tool_demo_pipeline",
    description="Full pipeline: research (with callbacks) -> write (with artifacts).",
    sub_agents=[research_agent, writer_agent],
)
