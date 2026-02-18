"""闲聊兜底 Agent——处理非采购相关的对话。"""

from google.adk.agents.llm_agent import LlmAgent

chitchat_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="chitchat_agent",
    description="Handles casual conversation and general questions.",
    instruction=(
        "You are a friendly sourcing assistant.\n"
        "Handle casual conversation briefly.\n"
        "Remind the user you can help with:\n"
        "- Searching products and suppliers\n"
        "- Getting price quotes\n"
        "- Comparing options\n"
    ),
)
