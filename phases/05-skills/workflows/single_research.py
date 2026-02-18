"""单领域研究——渐进加载 demo。

skilled_agent 启动时只有技能目录，没有具体工具。
LLM 分析用户请求后调用 activate_skill → 工具动态出现 → 执行研究。

这是本阶段最核心的演示：tool 的按需加载。
"""

from agents.skilled_agent import skilled_agent

single_research_agent = skilled_agent
