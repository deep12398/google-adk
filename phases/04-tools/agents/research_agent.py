from google.adk.agents.llm_agent import LlmAgent

from tools.search_tool import search_web
from callbacks.tool_callbacks import (
    audit_after,
    handle_tool_error,
    log_and_validate_before,
)


research_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="research_agent",
    description="Searches for information and extracts key points on a topic.",
    instruction=(
        "You are a research specialist. When given a topic:\n"
        "1. Call search_web to find information (try 2-3 different queries).\n"
        "2. Synthesize the results into 4-6 bullet points.\n"
        "3. Note the search count from state if available.\n\n"
        "If a search fails, acknowledge the error and work with available data."
    ),
    tools=[search_web],
    before_tool_callback=log_and_validate_before,
    after_tool_callback=audit_after,
    on_tool_error_callback=handle_tool_error,
    output_key="research_notes",
)
