"""复合评估器——加权组合多个 Evaluator 的评分。

灵感来自 n6-agent 的综合评分：
  overall_rag_score = retrieval_score * 0.4 + generation_score * 0.6

真实项目中，单一指标无法全面衡量 Agent 质量。你通常需要：
  - 工具轨迹是否正确？（行为）
  - 回答和参考答案像不像？（内容）
  - 回答是否基于工具输出？（忠实度）
  - 回答质量如何？（长度、结构）

CompositeEvaluator 允许你组合任意数量的 Evaluator，各配不同权重，
得到一个 0~1 的综合分数 + 各维度的分数明细。

用法：
    composite = CompositeEvaluator(
        evaluators={
            "trajectory": (TrajectoryEvaluator(threshold=0.8), 0.3),
            "faithfulness": (FaithfulnessEvaluator(), 0.4),
            "quality": (QualityEvaluator(), 0.3),
        },
        threshold=0.5,
    )
    result = composite.evaluate_invocations(actual, expected)
    # result.overall_score = 加权综合分
    # result.details = 各维度分数明细
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from google.adk.evaluation.eval_case import Invocation
from google.adk.evaluation.eval_metrics import EvalStatus
from google.adk.evaluation.evaluator import (
    EvaluationResult,
    Evaluator,
    PerInvocationResult,
)


@dataclass
class CompositeResult:
    """复合评测的详细结果。"""

    overall_score: float
    dimension_scores: dict[str, float]
    dimension_weights: dict[str, float]
    dimension_statuses: dict[str, str]


class CompositeEvaluator(Evaluator):
    """加权复合评估器。

    将多个 Evaluator 的评分按权重组合，输出综合分数 + 各维度明细。

    参数：
        evaluators: dict[name, (evaluator, weight)]
            每个评估器的名称、实例和权重。权重会自动归一化。
        threshold: float
            综合分数的通过阈值（默认 0.5）。
    """

    def __init__(
        self,
        evaluators: dict[str, tuple[Evaluator, float]],
        threshold: float = 0.5,
    ):
        self._evaluators = evaluators
        self._threshold = threshold

        # 归一化权重
        total_weight = sum(w for _, w in evaluators.values())
        self._normalized_weights = {
            name: w / total_weight
            for name, (_, w) in evaluators.items()
        }

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

        # 运行所有子评估器
        dimension_results: dict[str, EvaluationResult] = {}
        for name, (evaluator, _) in self._evaluators.items():
            dimension_results[name] = evaluator.evaluate_invocations(
                actual_invocations, expected_invocations
            )

        # 按维度收集分数
        dimension_scores: dict[str, float] = {}
        dimension_statuses: dict[str, str] = {}
        for name, result in dimension_results.items():
            dimension_scores[name] = result.overall_score or 0.0
            dimension_statuses[name] = result.overall_eval_status.name

        # 加权综合分
        overall_score = round(
            sum(
                dimension_scores[name] * self._normalized_weights[name]
                for name in self._evaluators
            ),
            3,
        )

        # 构建 per-invocation results（取第一个子评估器的 invocation 列表）
        first_result = next(iter(dimension_results.values()))
        per_results = []
        for i, pr in enumerate(first_result.per_invocation_results):
            # 每个 invocation 的加权综合分
            inv_scores = {}
            for name, result in dimension_results.items():
                if i < len(result.per_invocation_results):
                    inv_scores[name] = result.per_invocation_results[i].score or 0.0
                else:
                    inv_scores[name] = 0.0

            inv_overall = round(
                sum(
                    inv_scores[name] * self._normalized_weights[name]
                    for name in self._evaluators
                ),
                3,
            )

            per_results.append(
                PerInvocationResult(
                    actual_invocation=pr.actual_invocation,
                    expected_invocation=pr.expected_invocation,
                    score=inv_overall,
                    eval_status=(
                        EvalStatus.PASSED
                        if inv_overall >= self._threshold
                        else EvalStatus.FAILED
                    ),
                )
            )

        # 保存明细供外部访问
        self.last_composite_result = CompositeResult(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            dimension_weights=dict(self._normalized_weights),
            dimension_statuses=dimension_statuses,
        )

        return EvaluationResult(
            overall_score=overall_score,
            overall_eval_status=(
                EvalStatus.PASSED
                if overall_score >= self._threshold
                else EvalStatus.FAILED
            ),
            per_invocation_results=per_results,
        )

    def print_report(self) -> None:
        """打印各维度评分明细。"""
        if not hasattr(self, "last_composite_result"):
            print("  (No evaluation results yet)")
            return

        cr = self.last_composite_result
        print(f"  Overall: {cr.overall_score:.3f}")
        print(f"  Dimensions:")
        for name in self._evaluators:
            score = cr.dimension_scores[name]
            weight = cr.dimension_weights[name]
            status = cr.dimension_statuses[name]
            weighted = score * weight
            print(
                f"    {name:20s}  score={score:.3f}  "
                f"weight={weight:.1%}  "
                f"weighted={weighted:.3f}  "
                f"status={status}"
            )
