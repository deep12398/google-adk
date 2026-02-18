"""Q&A Agent——分析搜索结果、对比供应商。

output_key="qa_output" 将分析结果写入 state，
下游 Agent（如 quote_agent）可通过 {qa_output} 引用。
instruction 中的 {all_results} 由 ADK 自动从 state 注入。
"""

from google.genai import types

from google.adk.agents.llm_agent import LlmAgent

from tools.qa_tools import compare_products, get_product_details

qa_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="qa_agent",
    description="Analyzes search results, compares products and suppliers.",
    instruction=(
        "You are a sourcing Q&A specialist.\n\n"
        "## Your Capabilities\n"
        "- Compare products side by side using compare_products\n"
        "- Get detailed info on a product using get_product_details\n"
        "- Analyze and summarize search results\n\n"
        "## Available Context\n"
        "Search results: {all_results}\n\n"
        "## Guidelines\n"
        "- Present comparisons in table format\n"
        "- Highlight pros/cons of each option\n"
        "- Recommend the best option based on requirements\n"
    ),
    tools=[compare_products, get_product_details],
    output_key="qa_output",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
    ),
)
