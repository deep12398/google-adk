"""自定义评估器测试——验证 QualityEvaluator 的行为。

测试 QualityEvaluator 的两个检查维度：
  1. 工具调用检查（50% 权重）
  2. 响应长度检查（50% 权重）
"""

import pytest
from google.genai import types

from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalStatus

import sys
from pathlib import Path

# 确保能 import evaluators 模块
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from evaluators.custom_evaluator import QualityEvaluator


# ---------- 辅助函数 ----------


def _make_invocation(
    query: str,
    tool_calls: list[tuple[str, dict]] | None = None,
    response: str = "",
) -> Invocation:
    """构造 Invocation 对象。"""
    intermediate = None
    if tool_calls:
        intermediate = IntermediateData(
            tool_uses=[
                types.FunctionCall(name=name, args=args)
                for name, args in tool_calls
            ],
        )

    return Invocation(
        user_content=types.Content(
            parts=[types.Part.from_text(text=query)],
            role="user",
        ),
        final_response=types.Content(
            parts=[types.Part.from_text(text=response)],
            role="model",
        ),
        intermediate_data=intermediate,
    )


# ---------- 测试用例 ----------


class TestQualityEvaluator:
    """QualityEvaluator 单元测试。"""

    def test_both_checks_pass(self):
        """有 search_web 调用 + 响应足够长 → 1.0。"""
        evaluator = QualityEvaluator(
            required_tool="search_web",
            min_response_length=10,
        )

        actual = [
            _make_invocation(
                "Research AI",
                [("search_web", {"query": "AI"})],
                "AI trends include automation, scalability, and deep learning advances.",
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score == 1.0
        assert result.overall_eval_status == EvalStatus.PASSED

    def test_no_tool_call(self):
        """没有调用 search_web → tool_use_score=0，总分 0.5。"""
        evaluator = QualityEvaluator(
            required_tool="search_web",
            min_response_length=10,
        )

        actual = [
            _make_invocation(
                "Research AI",
                None,  # 没有工具调用
                "AI is a broad field covering many topics and applications.",
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score == 0.5  # 只有 length 通过

    def test_short_response(self):
        """响应太短 → length_score=0，总分 0.5。"""
        evaluator = QualityEvaluator(
            required_tool="search_web",
            min_response_length=100,
        )

        actual = [
            _make_invocation(
                "Research AI",
                [("search_web", {"query": "AI"})],
                "AI is great.",  # 太短
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score == 0.5  # 只有 tool_use 通过

    def test_both_fail(self):
        """没有工具调用 + 响应太短 → 0.0。"""
        evaluator = QualityEvaluator(
            required_tool="search_web",
            min_response_length=100,
        )

        actual = [
            _make_invocation("Research AI", None, "OK.")
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score == 0.0
        assert result.overall_eval_status == EvalStatus.FAILED

    def test_empty_invocations(self):
        """空列表 → NOT_EVALUATED。"""
        evaluator = QualityEvaluator()
        result = evaluator.evaluate_invocations([])
        assert result.overall_score == 0.0
        assert result.overall_eval_status == EvalStatus.NOT_EVALUATED

    def test_multiple_invocations_averaged(self):
        """多个 Invocation 的分数取平均。"""
        evaluator = QualityEvaluator(
            required_tool="search_web",
            min_response_length=10,
        )

        actual = [
            # 两个检查都通过 → 1.0
            _make_invocation(
                "Q1",
                [("search_web", {"query": "A"})],
                "A comprehensive answer about topic A with enough words.",
            ),
            # 两个检查都失败 → 0.0
            _make_invocation("Q2", None, "Short."),
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score == 0.5  # (1.0 + 0.0) / 2

    def test_wrong_tool_name(self):
        """调用了其他工具但不是 required_tool → tool_use_score=0。"""
        evaluator = QualityEvaluator(
            required_tool="search_web",
            min_response_length=10,
        )

        actual = [
            _make_invocation(
                "Research AI",
                [("other_tool", {"query": "AI"})],
                "Some sufficiently long response about AI trends.",
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score == 0.5  # 只有 length 通过
