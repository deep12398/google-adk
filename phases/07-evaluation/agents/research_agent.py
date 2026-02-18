"""被测 Agent——评测的目标对象。

一个简单的研究助手：接收用户问题 → 调用 search_web 搜索 → 总结返回。
评测要验证的就是：
  1. Agent 是否调用了 search_web（工具轨迹）
  2. Agent 的最终回答是否合理（响应匹配）
"""

from google.adk.agents import LlmAgent

from tools.search_tool import search_web

research_agent = LlmAgent(
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
