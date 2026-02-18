"""意图分类评估器——验证 classify_intent 是否被调用且分类正确。"""

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


class IntentEvaluator(Evaluator):
    """验证意图分类工具是否被正确调用。"""

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
        for i, inv in enumerate(actual_invocations):
            tool_calls = get_all_tool_calls(inv.intermediate_data)
            has_classify = any(tc.name == "classify_intent" for tc in tool_calls)
            score = 1.0 if has_classify else 0.0

            per_results.append(
                PerInvocationResult(
                    actual_invocation=inv,
                    expected_invocation=(
                        expected_invocations[i]
                        if expected_invocations and i < len(expected_invocations)
                        else None
                    ),
                    score=score,
                    eval_status=(
                        EvalStatus.PASSED if score >= 0.5
                        else EvalStatus.FAILED
                    ),
                )
            )

        overall = mean(r.score for r in per_results) if per_results else 0.0
        return EvaluationResult(
            overall_score=overall,
            overall_eval_status=(
                EvalStatus.PASSED if overall >= 0.5
                else EvalStatus.FAILED
            ),
            per_invocation_results=per_results,
        )
