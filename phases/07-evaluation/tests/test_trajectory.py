"""工具轨迹评测——TrajectoryEvaluator 手动测试。

演示 TrajectoryEvaluator 的三种匹配模式：
  - EXACT：完全匹配（不允许多余或缺少）
  - IN_ORDER：顺序匹配（允许有额外调用）
  - ANY_ORDER：存在即可（不管顺序）

手动构造 Invocation 对象，不需要实际运行 Agent。
"""

import pytest
from google.genai import types

from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus
from google.adk.evaluation.trajectory_evaluator import (
    TrajectoryEvaluator,
    ToolTrajectoryCriterion,
)


# ---------- 辅助函数 ----------


def _make_invocation(
    query: str,
    tool_calls: list[tuple[str, dict]],
    response: str = "some response",
) -> Invocation:
    """构造一个 Invocation 对象。

    Args:
        query: 用户输入。
        tool_calls: [(tool_name, args), ...] 工具调用列表。
        response: Agent 最终响应文本。
    """
    return Invocation(
        user_content=types.Content(
            parts=[types.Part.from_text(text=query)],
            role="user",
        ),
        final_response=types.Content(
            parts=[types.Part.from_text(text=response)],
            role="model",
        ),
        intermediate_data=IntermediateData(
            tool_uses=[
                types.FunctionCall(name=name, args=args)
                for name, args in tool_calls
            ],
        ),
    )


# ---------- 测试用例 ----------


class TestTrajectoryExactMatch:
    """EXACT 模式：actual 必须与 expected 完全一致。"""

    def _make_evaluator(self) -> TrajectoryEvaluator:
        return TrajectoryEvaluator(
            eval_metric=EvalMetric(
                metric_name="tool_trajectory_avg_score",
                threshold=1.0,
                criterion=ToolTrajectoryCriterion(
                    threshold=1.0,
                    match_type=ToolTrajectoryCriterion.MatchType.EXACT,
                ),
            ),
        )

    def test_perfect_match(self):
        """完全匹配 → 1.0。"""
        evaluator = self._make_evaluator()

        actual = [
            _make_invocation(
                "Research AI",
                [("search_web", {"query": "AI trends"})],
            )
        ]
        expected = [
            _make_invocation(
                "Research AI",
                [("search_web", {"query": "AI trends"})],
            )
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score == 1.0
        assert result.overall_eval_status == EvalStatus.PASSED

    def test_extra_tool_call_fails(self):
        """actual 多了一个工具调用 → 0.0。"""
        evaluator = self._make_evaluator()

        actual = [
            _make_invocation(
                "Research AI",
                [
                    ("search_web", {"query": "AI trends"}),
                    ("search_web", {"query": "AI news"}),  # 多出的调用
                ],
            )
        ]
        expected = [
            _make_invocation(
                "Research AI",
                [("search_web", {"query": "AI trends"})],
            )
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score == 0.0

    def test_missing_tool_call_fails(self):
        """actual 缺少工具调用 → 0.0。"""
        evaluator = self._make_evaluator()

        actual = [_make_invocation("Research AI", [])]  # 没有工具调用
        expected = [
            _make_invocation(
                "Research AI",
                [("search_web", {"query": "AI trends"})],
            )
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score == 0.0


class TestTrajectoryInOrder:
    """IN_ORDER 模式：expected 中的调用必须按顺序出现，允许中间有额外调用。"""

    def _make_evaluator(self) -> TrajectoryEvaluator:
        return TrajectoryEvaluator(
            eval_metric=EvalMetric(
                metric_name="tool_trajectory_avg_score",
                threshold=1.0,
                criterion=ToolTrajectoryCriterion(
                    threshold=1.0,
                    match_type=ToolTrajectoryCriterion.MatchType.IN_ORDER,
                ),
            ),
        )

    def test_exact_also_passes(self):
        """完全匹配也通过。"""
        evaluator = self._make_evaluator()

        calls = [("search_web", {"query": "AI"})]
        actual = [_make_invocation("AI", calls)]
        expected = [_make_invocation("AI", calls)]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score == 1.0

    def test_extra_calls_in_between_passes(self):
        """中间有额外调用但顺序正确 → 通过。"""
        evaluator = self._make_evaluator()

        actual = [
            _make_invocation(
                "AI",
                [
                    ("search_web", {"query": "AI"}),
                    ("other_tool", {"x": 1}),  # 额外调用
                    ("search_web", {"query": "ML"}),
                ],
            )
        ]
        expected = [
            _make_invocation(
                "AI",
                [
                    ("search_web", {"query": "AI"}),
                    ("search_web", {"query": "ML"}),
                ],
            )
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score == 1.0


class TestTrajectoryAnyOrder:
    """ANY_ORDER 模式：expected 中的调用只要存在即可，不管顺序。"""

    def _make_evaluator(self) -> TrajectoryEvaluator:
        return TrajectoryEvaluator(
            eval_metric=EvalMetric(
                metric_name="tool_trajectory_avg_score",
                threshold=1.0,
                criterion=ToolTrajectoryCriterion(
                    threshold=1.0,
                    match_type=ToolTrajectoryCriterion.MatchType.ANY_ORDER,
                ),
            ),
        )

    def test_reversed_order_passes(self):
        """顺序反了也通过。"""
        evaluator = self._make_evaluator()

        actual = [
            _make_invocation(
                "AI",
                [
                    ("search_web", {"query": "ML"}),
                    ("search_web", {"query": "AI"}),
                ],
            )
        ]
        expected = [
            _make_invocation(
                "AI",
                [
                    ("search_web", {"query": "AI"}),
                    ("search_web", {"query": "ML"}),
                ],
            )
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score == 1.0


class TestTrajectoryThreshold:
    """阈值机制：score >= threshold → PASSED，否则 FAILED。"""

    def test_threshold_boundary(self):
        """多个 invocation 部分匹配，平均分决定通过与否。"""
        evaluator = TrajectoryEvaluator(threshold=0.5)

        # 第一个匹配，第二个不匹配 → 平均 0.5
        actual = [
            _make_invocation("Q1", [("search_web", {"query": "A"})]),
            _make_invocation("Q2", [("wrong_tool", {"query": "B"})]),
        ]
        expected = [
            _make_invocation("Q1", [("search_web", {"query": "A"})]),
            _make_invocation("Q2", [("search_web", {"query": "B"})]),
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score == 0.5
        assert result.overall_eval_status == EvalStatus.PASSED
