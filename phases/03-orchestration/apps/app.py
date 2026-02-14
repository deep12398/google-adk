from pathlib import Path
import os
import sys

from google.adk.apps import App

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from workflows.delegation import delegation_agent  # noqa: E402
from workflows.loop_refine import loop_agent  # noqa: E402
from workflows.parallel_research import parallel_agent  # noqa: E402
from workflows.sequential_pipeline import pipeline_agent  # noqa: E402


WORKFLOW = os.getenv("WORKFLOW", "sequential").lower()
ROOT_AGENTS = {
    "sequential": pipeline_agent,
    "parallel": parallel_agent,
    "loop": loop_agent,
    "delegation": delegation_agent,
}

root_agent = ROOT_AGENTS.get(WORKFLOW, pipeline_agent)

app = App(
    name=f"orchestration_{WORKFLOW}",
    root_agent=root_agent,
)
