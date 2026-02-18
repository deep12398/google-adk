"""自定义评估器——继承 Evaluator ABC。

演示如何编写自定义评测逻辑，不依赖 LLM Judge：
  1. 工具调用检查：Agent 是否调用了 search_web？
  2. 响应长度检查：最终响应是否超过最低字数？

两个检查各占 50% 权重，组合为 0~1 的评分。

底层机制：
  - Evaluator ABC 定义了 evaluate_invocations(actual, expected) → EvaluationResult
  - 所有评估器都实现这个接口
  - actual_invocations 是 Agent 实际运行产生的 Invocation 列表
  - expected_invocations 是评测集中的参考 Invocation 列表（可选）
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


def _extract_text(content) -> str:
    """从 Content 对象中提取纯文本。"""
    if content is None:
        return ""
    if hasattr(content, "parts") and content.parts:
        return " ".join(
            part.text for part in content.parts if hasattr(part, "text") and part.text
        )
    return ""


class QualityEvaluator(Evaluator):
    """自定义质量评估器。

    检查两个维度：
      - tool_use_score (0.5 权重)：Agent 是否调用了指定工具？
      - length_score (0.5 权重)：最终响应是否达到最低字数？

    用法：
        evaluator = QualityEvaluator(
            required_tool="search_web",
            min_response_length=50,
        )
        result = evaluator.evaluate_invocations(actual, expected)
    """

    def __init__(
        self,
        required_tool: str = "search_web",
        min_response_length: int = 50,
    ):
        self._required_tool = required_tool
        self._min_response_length = min_response_length

    def evaluate_invocations(
        self,
        actual_invocations: list[Invocation],
        expected_invocations: Optional[list[Invocation]] = None,
    ) -> EvaluationResult:
        """对每个 Invocation 评分，然后汇总。"""
        if not actual_invocations:
            return EvaluationResult(
                overall_score=0.0,
                overall_eval_status=EvalStatus.NOT_EVALUATED,
                per_invocation_results=[],
            )

        per_results: list[PerInvocationResult] = []

        for i, inv in enumerate(actual_invocations):
            # --- 检查 1：是否调用了指定工具 ---
            tool_calls = get_all_tool_calls(inv.intermediate_data)
            has_required_tool = any(
                tc.name == self._required_tool for tc in tool_calls
            )
            tool_use_score = 1.0 if has_required_tool else 0.0

            # --- 检查 2：响应长度是否达标 ---
            response_text = _extract_text(inv.final_response)
            long_enough = len(response_text) >= self._min_response_length
            length_score = 1.0 if long_enough else 0.0

            # --- 加权汇总 ---
            score = tool_use_score * 0.5 + length_score * 0.5

            expected_inv = (
                expected_invocations[i]
                if expected_invocations and i < len(expected_invocations)
                else None
            )

            per_results.append(
                PerInvocationResult(
                    actual_invocation=inv,
                    expected_invocation=expected_inv,
                    score=score,
                    eval_status=(
                        EvalStatus.PASSED if score >= 0.5 else EvalStatus.FAILED
                    ),
                )
            )

        overall = mean(r.score for r in per_results if r.score is not None)
        return EvaluationResult(
            overall_score=overall,
            overall_eval_status=(
                EvalStatus.PASSED if overall >= 0.5 else EvalStatus.FAILED
            ),
            per_invocation_results=per_results,
        )
