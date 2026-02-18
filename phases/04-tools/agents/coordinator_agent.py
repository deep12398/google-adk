from google.adk.agents.llm_agent import LlmAgent

from callbacks.tool_callbacks import (
    audit_after,
    handle_tool_error,
    log_and_validate_before,
)
from tools.agent_as_tool import review_tool
from tools.confirm_tool import publish_tool
from tools.search_tool import search_web


coordinator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="coordinator",
    description="Coordinates research, review, and publication using specialized tools.",
    instruction=(
        "You coordinate a research report workflow:\n"
        "1. Use search_web to gather information.\n"
        "2. Write a brief report based on findings.\n"
        "3. Use reviewer_agent tool to get quality feedback.\n"
        "4. Use publish_report to publish the final version (requires confirmation).\n\n"
        "Always explain what you're doing at each step."
    ),
    tools=[search_web, review_tool, publish_tool],
    before_tool_callback=log_and_validate_before,
    after_tool_callback=audit_after,
    on_tool_error_callback=handle_tool_error,
)
