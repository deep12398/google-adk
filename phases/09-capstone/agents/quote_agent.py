"""报价 Agent——生成报价单 + 保存为 artifact。

使用 save_document（来自 memory_tools）将报价保存为版本化 artifact。
instruction 中的 {requirements} 由 ADK 从 state 注入（requirements_agent 写入）。
"""

from google.genai import types

from google.adk.agents.llm_agent import LlmAgent

from tools.memory_tools import save_document
from tools.quote_tools import generate_quote

quote_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="quote_agent",
    description="Generates price quotes based on requirements and selected products.",
    instruction=(
        "You are a quote generation specialist.\n\n"
        "## Workflow\n"
        "1. Review the user's requirements: {requirements}\n"
        "2. Use generate_quote to create a formal quote.\n"
        "3. Save the quote document using save_document.\n"
        "4. Present the quote summary to the user.\n\n"
        "## Format\n"
        "Present quotes professionally with all key terms.\n"
    ),
    tools=[generate_quote, save_document],
    output_key="quote_output",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=1000,
    ),
)
