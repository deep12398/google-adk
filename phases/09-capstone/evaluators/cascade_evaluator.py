"""级联搜索评估器——验证 3 级搜索的执行顺序。

规则：
  - Tier 1 (search_catalog) 必须在 Tier 2 (search_suppliers) 之前
  - Tier 2 必须在 Tier 3 (search_external) 之前
  - 乱序扣分
"""

from __future__ import annotations

from statistics import mean
from typing import Optional

from google.adk.evaluation.eval_case import Invocation, get_all_tool_calls
from google.adk.evaluation.eval_metrics import EvalStatus
from google.adk.evaluation.evaluator import (
    EvaluationResult,
    Evaluator,
    PerInvocationResult,
)

# 工具名 → 层级编号
TIER_ORDER = {
    "search_catalog": 1,
    "search_suppliers": 2,
    "search_external": 3,
}


class CascadeEvaluator(Evaluator):
    """验证 3 级级联搜索遵循正确顺序。"""

    def __init__(self, threshold: float = 0.5) -> None:
        self._threshold = threshold

    def evaluate_invocations(
        self,
        actual_invocations: list[Invocation],
        expected_invocations: Optional[list[Invocation]] = None,
    ) -> EvaluationResult:
        if not actual_invocations:
            return EvaluationResult(
                overall_score=0.0,
                overall_eval_status=EvalStatus.NOT_EVALUATED,
                per_invocation_results=[],
            )

        per_results = []
        for inv in actual_invocations:
            tool_calls = get_all_tool_calls(inv.intermediate_data)
            tool_names = [tc.name for tc in tool_calls]

            # 提取搜索工具的调用顺序
            tier_calls = [
                (TIER_ORDER[name], name)
                for name in tool_names
                if name in TIER_ORDER
            ]

            # 评分：层级必须递增
            score = 1.0
            for i in range(1, len(tier_calls)):
                if tier_calls[i][0] < tier_calls[i - 1][0]:
                    score -= 0.5  # 乱序扣 0.5

            score = max(score, 0.0)

            per_results.append(
                PerInvocationResult(
                    actual_invocation=inv,
                    expected_invocation=None,
                    score=score,
                    eval_status=(
                        EvalStatus.PASSED if score >= self._threshold
                        else EvalStatus.FAILED
                    ),
                )
            )

        overall = mean(r.score for r in per_results) if per_results else 0.0
        return EvaluationResult(
            overall_score=overall,
            overall_eval_status=(
                EvalStatus.PASSED if overall >= self._threshold
                else EvalStatus.FAILED
            ),
            per_invocation_results=per_results,
        )
