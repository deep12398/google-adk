"""App 定义——供 AgentEvaluator 使用。

AgentEvaluator.evaluate(agent_module=...) 会加载模块中的 root_agent。
本文件提供标准 App 定义，评测入口 main.py 会引用。
"""

import sys
from pathlib import Path

from google.adk.agents import LlmAgent

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.search_tool import search_web

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="research_agent",
    instruction=(
        "You are a research assistant. "
        "When the user asks about a topic, use the search_web tool to find information, "
        "then provide a clear, comprehensive summary of the findings. "
        "Always cite the sources from search results."
    ),
    tools=[search_web],
)
