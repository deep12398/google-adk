"""复合评估器 + 报告生成器测试。

测试：
  1. CompositeEvaluator 正确加权组合多个评估器
  2. MetricsReporter 正确生成结构化报告
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest
from google.genai import types

from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalStatus
from google.adk.evaluation.trajectory_evaluator import TrajectoryEvaluator

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from evaluators.custom_evaluator import QualityEvaluator
from evaluators.faithfulness_evaluator import FaithfulnessEvaluator
from evaluators.composite_evaluator import CompositeEvaluator
from evaluators.metrics_reporter import MetricsReporter


# ---------- 辅助函数 ----------


def _make_invocation(
    query: str,
    tool_calls: list[tuple[str, dict]] | None = None,
    tool_responses: list[tuple[str, dict]] | None = None,
    response: str = "",
) -> Invocation:
    intermediate = None
    if tool_calls or tool_responses:
        intermediate = IntermediateData(
            tool_uses=[
                types.FunctionCall(name=n, args=a)
                for n, a in (tool_calls or [])
            ],
            tool_responses=[
                types.FunctionResponse(name=n, response=r)
                for n, r in (tool_responses or [])
            ],
        )
    return Invocation(
        user_content=types.Content(
            parts=[types.Part.from_text(text=query)], role="user",
        ),
        final_response=types.Content(
            parts=[types.Part.from_text(text=response)], role="model",
        ),
        intermediate_data=intermediate,
    )


# ---------- CompositeEvaluator 测试 ----------


class TestCompositeEvaluator:

    def test_all_pass(self):
        """所有子评估器都通过 → 高综合分。"""
        composite = CompositeEvaluator(
            evaluators={
                "trajectory": (TrajectoryEvaluator(threshold=0.5), 0.5),
                "quality": (QualityEvaluator(min_response_length=10), 0.5),
            },
            threshold=0.5,
        )

        actual = [
            _make_invocation(
                "Research AI",
                tool_calls=[("search_web", {"query": "AI"})],
                response="AI is a broad and exciting field with many applications.",
            )
        ]
        expected = [
            _make_invocation(
                "Research AI",
                tool_calls=[("search_web", {"query": "AI"})],
                response="Reference",
            )
        ]

        result = composite.evaluate_invocations(actual, expected)
        assert result.overall_score == 1.0
        assert result.overall_eval_status == EvalStatus.PASSED

    def test_partial_pass(self):
        """部分通过 → 中间分数。"""
        composite = CompositeEvaluator(
            evaluators={
                "trajectory": (TrajectoryEvaluator(threshold=0.5), 0.5),
                "quality": (QualityEvaluator(min_response_length=10), 0.5),
            },
            threshold=0.5,
        )

        actual = [
            _make_invocation(
                "Research AI",
                tool_calls=[("wrong_tool", {"query": "AI"})],  # 轨迹错误
                response="AI is a broad and exciting field with many applications.",  # 质量通过
            )
        ]
        expected = [
            _make_invocation(
                "Research AI",
                tool_calls=[("search_web", {"query": "AI"})],
            )
        ]

        result = composite.evaluate_invocations(actual, expected)
        assert 0.0 < result.overall_score < 1.0

    def test_weight_normalization(self):
        """权重自动归一化。"""
        composite = CompositeEvaluator(
            evaluators={
                "a": (QualityEvaluator(min_response_length=10), 3.0),
                "b": (QualityEvaluator(min_response_length=10), 7.0),
            },
        )

        # 3/(3+7) = 0.3, 7/(3+7) = 0.7
        assert abs(composite._normalized_weights["a"] - 0.3) < 0.001
        assert abs(composite._normalized_weights["b"] - 0.7) < 0.001

    def test_composite_result_details(self):
        """last_composite_result 包含各维度明细。"""
        composite = CompositeEvaluator(
            evaluators={
                "trajectory": (TrajectoryEvaluator(threshold=0.5), 0.5),
                "quality": (QualityEvaluator(min_response_length=10), 0.5),
            },
        )

        actual = [
            _make_invocation(
                "AI", [("search_web", {"query": "AI"})],
                response="Some response about AI topics and trends.",
            )
        ]
        expected = [
            _make_invocation("AI", [("search_web", {"query": "AI"})]),
        ]

        composite.evaluate_invocations(actual, expected)
        cr = composite.last_composite_result

        assert "trajectory" in cr.dimension_scores
        assert "quality" in cr.dimension_scores
        assert "trajectory" in cr.dimension_weights
        assert cr.dimension_scores["trajectory"] == 1.0  # 完全匹配

    def test_three_evaluators(self):
        """三个评估器组合。"""
        composite = CompositeEvaluator(
            evaluators={
                "trajectory": (TrajectoryEvaluator(threshold=0.5), 0.3),
                "faithfulness": (FaithfulnessEvaluator(), 0.4),
                "quality": (QualityEvaluator(min_response_length=10), 0.3),
            },
        )

        actual = [
            _make_invocation(
                "Research AI",
                tool_calls=[("search_web", {"query": "AI"})],
                tool_responses=[("search_web", {"snippet": "AI automation scalability"})],
                response="AI trends include automation and scalability in modern systems.",
            )
        ]
        expected = [
            _make_invocation("Research AI", [("search_web", {"query": "AI"})]),
        ]

        result = composite.evaluate_invocations(actual, expected)
        assert result.overall_score > 0.5


# ---------- MetricsReporter 测试 ----------


class TestMetricsReporter:

    def test_empty_report(self):
        """空报告。"""
        reporter = MetricsReporter()
        report = reporter.generate_report()
        assert report["evaluation_summary"]["total_cases"] == 0
        assert report["evaluation_summary"]["pass_rate"] == 0.0

    def test_add_results_and_summarize(self):
        """添加结果并生成摘要。"""
        reporter = MetricsReporter()

        reporter.add_result("case_1", {"trajectory": 1.0, "quality": 0.8}, "PASSED")
        reporter.add_result("case_2", {"trajectory": 0.0, "quality": 0.5}, "FAILED")

        report = reporter.generate_report()
        summary = report["evaluation_summary"]

        assert summary["total_cases"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 0.5

        # 检查 avg/min/max
        traj = summary["average_metrics"]["trajectory"]
        assert traj["avg"] == 0.5
        assert traj["min"] == 0.0
        assert traj["max"] == 1.0

    def test_save_report(self):
        """保存报告到 JSON 文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = MetricsReporter(report_dir=tmpdir)
            reporter.add_result("case_1", {"score": 0.9}, "PASSED")

            path = reporter.save_report(filename="test_report.json")

            assert path.exists()
            with open(path) as f:
                data = json.load(f)
            assert data["evaluation_summary"]["total_cases"] == 1

    def test_metadata_preserved(self):
        """元数据在报告中保留。"""
        reporter = MetricsReporter()
        reporter.add_result(
            "case_1",
            {"score": 0.9},
            "PASSED",
            metadata={"composite_score": 0.85, "query": "test query"},
        )

        report = reporter.generate_report()
        detail = report["detailed_results"][0]
        assert detail["metadata"]["composite_score"] == 0.85
        assert detail["metadata"]["query"] == "test query"
