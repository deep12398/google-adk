from google.adk.agents.sequential_agent import SequentialAgent

from agents.qa_agent import qa_agent
from agents.research_agent import research_agent
from agents.write_agent import write_agent


pipeline_agent = SequentialAgent(
    name="report_pipeline",
    description="Sequential research → write → QA pipeline.",
    sub_agents=[research_agent, write_agent, qa_agent],
)
