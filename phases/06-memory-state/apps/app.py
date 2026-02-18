from pathlib import Path
import os
import sys

from google.adk.apps import App

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from workflows.state_demo import state_demo_agent  # noqa: E402
from workflows.memory_demo import memory_demo_agent  # noqa: E402

DEMO = os.getenv("DEMO", "state").lower()
ROOT_AGENTS = {
    "state": state_demo_agent,
    "memory": memory_demo_agent,
}

root_agent = ROOT_AGENTS.get(DEMO, state_demo_agent)

app = App(
    name=f"memory_state_{DEMO}",
    root_agent=root_agent,
)
