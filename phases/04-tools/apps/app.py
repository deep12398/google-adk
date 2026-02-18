from pathlib import Path
import os
import sys

from google.adk.apps import App

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from agents.research_agent import research_agent  # noqa: E402
from agents.coordinator_agent import coordinator_agent  # noqa: E402
from workflows.tool_demo_pipeline import pipeline_agent  # noqa: E402


DEMO = os.getenv("DEMO", "basics").lower()
ROOT_AGENTS = {
    "basics": research_agent,  # FunctionTool + ToolContext + callbacks
    "agent_tool": coordinator_agent,  # AgentTool + confirmation
    "pipeline": pipeline_agent,  # Full pipeline
}

root_agent = ROOT_AGENTS.get(DEMO, research_agent)

app = App(
    name=f"tools_{DEMO}",
    root_agent=root_agent,
)
