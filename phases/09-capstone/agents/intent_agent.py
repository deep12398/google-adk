"""意图分类 Agent——调用 classify_intent 并输出结果。

output_key="classified_intent" 将分类结果写入 state，
供 orchestrator 的 instruction 中通过 {classified_intent} 引用。
"""

from google.adk.agents.llm_agent import LlmAgent

from tools.intent_tools import classify_intent

intent_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="intent_agent",
    description="Classifies user intent before routing to specialized agents.",
    instruction=(
        "You are an intent classifier for a sourcing assistant.\n\n"
        "1. Call classify_intent with the user's EXACT message.\n"
        "2. If confidence < 0.5, use your judgment to refine.\n"
        "3. Report the classified intent.\n"
    ),
    tools=[classify_intent],
    output_key="classified_intent",
)
