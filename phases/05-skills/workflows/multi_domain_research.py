"""多领域并行研究 → 汇总报告。

流程：ParallelAgent([tech, market, legal]) → report_agent

每个研究员通过 apply_skill 装载了各自的领域技能，
report_agent 用 include_contents="none" 只看 state 中的结构化结果。
"""

from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.specialists import tech_researcher, market_researcher, legal_researcher
from agents.report_agent import report_agent

parallel_research = ParallelAgent(
    name="parallel_research",
    description="Runs tech/market/legal research in parallel.",
    sub_agents=[tech_researcher, market_researcher, legal_researcher],
)

multi_domain_agent = SequentialAgent(
    name="multi_domain_research",
    description="Parallel multi-domain research followed by report synthesis.",
    sub_agents=[parallel_research, report_agent],
)
