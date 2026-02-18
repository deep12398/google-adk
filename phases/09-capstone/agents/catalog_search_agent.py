"""产品目录搜索 Agent——Step 1 的核心 Agent。

Step 5 起挂载 tool callbacks（验证、计时、结果充实）。
"""

from google.adk.agents.llm_agent import LlmAgent

from callbacks.sourcing_callbacks import (
    after_tool_cb,
    before_tool_cb,
    on_tool_error_cb,
)
from tools.catalog_tools import search_catalog

catalog_search_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="catalog_search_agent",
    description="Searches the internal product catalog for matching items.",
    instruction=(
        "You are a sourcing assistant that helps users find products.\n\n"
        "When the user describes what they need:\n"
        "1. Use search_catalog with relevant keywords.\n"
        "2. Present results in a clear table format:\n"
        "   | Name | Specs | Price Range | MOQ | Lead Time |\n"
        "3. If no results found, suggest broadening or rephrasing the search.\n"
        "4. Mention the total number of matches found.\n"
    ),
    tools=[search_catalog],
    before_tool_callback=before_tool_cb,
    after_tool_callback=after_tool_cb,
    on_tool_error_callback=on_tool_error_cb,
)
