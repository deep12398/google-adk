from pathlib import Path
import os
import sys

from google.adk.apps import App

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from workflows.multi_domain_research import multi_domain_agent  # noqa: E402
from workflows.single_research import single_research_agent  # noqa: E402

DEMO = os.getenv("DEMO", "single").lower()
ROOT_AGENTS = {
    "multi": multi_domain_agent,
    "single": single_research_agent,
}

root_agent = ROOT_AGENTS.get(DEMO, single_research_agent)

app = App(
    name=f"skills_{DEMO}",
    root_agent=root_agent,
)
