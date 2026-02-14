from pathlib import Path
import sys

from google.adk.apps import App

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from agents.root import root_agent  # noqa: E402


app = App(
    name="skeleton_app",
    root_agent=root_agent,
)
