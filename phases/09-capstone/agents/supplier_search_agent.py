"""Tier 2 供应商数据库搜索 Agent。

Step 5 起挂载 tool callbacks。
"""

from google.adk.agents.llm_agent import LlmAgent

from callbacks.sourcing_callbacks import (
    after_tool_cb,
    before_tool_cb,
    on_tool_error_cb,
)
from tools.supplier_tools import search_suppliers

supplier_search_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="supplier_search_agent",
    description="Searches the internal supplier database (Tier 2 cascade).",
    instruction=(
        "You are a supplier database search specialist.\n\n"
        "You are called when the product catalog has insufficient results.\n"
        "1. Generate 3-5 semantic query variations from the user's need.\n"
        "2. Call search_suppliers with the queries and category.\n"
        "3. Report results including both catalog and supplier matches.\n"
    ),
    tools=[search_suppliers],
    before_tool_callback=before_tool_cb,
    after_tool_callback=after_tool_cb,
    on_tool_error_callback=on_tool_error_cb,
)
