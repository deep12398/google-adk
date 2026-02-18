"""Tier 3 外部搜索 Agent。

Step 5 起挂载 tool callbacks。
"""

from google.adk.agents.llm_agent import LlmAgent

from callbacks.sourcing_callbacks import (
    after_tool_cb,
    before_tool_cb,
    on_tool_error_cb,
)
from tools.web_tools import search_external

web_search_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="web_search_agent",
    description="Searches external sources like Alibaba (Tier 3 fallback).",
    instruction=(
        "You are a web search specialist for sourcing.\n\n"
        "You are called when internal databases have insufficient results.\n"
        "1. Use search_external to find suppliers on external platforms.\n"
        "2. Clearly mark results as external and advise verification.\n"
    ),
    tools=[search_external],
    before_tool_callback=before_tool_cb,
    after_tool_callback=after_tool_cb,
    on_tool_error_callback=on_tool_error_cb,
)
