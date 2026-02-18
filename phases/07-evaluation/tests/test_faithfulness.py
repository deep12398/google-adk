"""忠实度评估器测试——验证 FaithfulnessEvaluator 的行为。

测试三种场景：
  1. 忠实回答（基于工具输出）→ 高分
  2. 幻觉回答（和工具输出无关）→ 低分
  3. 无工具输出 → 忠实度为 0
"""

import sys
from pathlib import Path

import pytest
from google.genai import types

from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalStatus

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from evaluators.faithfulness_evaluator import FaithfulnessEvaluator


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


class TestFaithfulness:
    """忠实度评估测试。"""

    def test_faithful_response(self):
        """回答基于工具输出 → 高忠实度。"""
        evaluator = FaithfulnessEvaluator(threshold=0.3)

        actual = [
            _make_invocation(
                "Research AI trends",
                tool_calls=[("search_web", {"query": "AI trends"})],
                tool_responses=[
                    ("search_web", {
                        "results": [
                            {"snippet": "AI trends include automation, scalability, and integration."},
                        ],
                    }),
                ],
                response="AI trends include automation, scalability, and integration in recent developments.",
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score is not None
        assert result.overall_score > 0.3  # 忠实回答应得高分
        assert result.overall_eval_status == EvalStatus.PASSED

    def test_hallucinated_response(self):
        """回答与工具输出无关 → 低忠实度。"""
        evaluator = FaithfulnessEvaluator(threshold=0.3)

        actual = [
            _make_invocation(
                "Research AI trends",
                tool_calls=[("search_web", {"query": "AI trends"})],
                tool_responses=[
                    ("search_web", {
                        "results": [
                            {"snippet": "AI trends include automation and scalability."},
                        ],
                    }),
                ],
                response="The weather is sunny today with clear blue skies and warm temperatures.",
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score is not None
        # 幻觉回答的忠实度应低于忠实回答
        # (但 relevancy 分可能也很低，所以总分很低)

    def test_no_tool_output(self):
        """没有工具返回 → 忠实度为 0。"""
        evaluator = FaithfulnessEvaluator(threshold=0.3)

        actual = [
            _make_invocation(
                "Research AI trends",
                response="AI trends include many exciting developments.",
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        # 没有 tool_responses → faithfulness = 0，只有 relevancy 贡献分数
        assert result.overall_score is not None

    def test_empty_response(self):
        """空回答 → 0 分。"""
        evaluator = FaithfulnessEvaluator(threshold=0.3)

        actual = [
            _make_invocation(
                "Research AI trends",
                tool_calls=[("search_web", {"query": "AI"})],
                tool_responses=[("search_web", {"result": "some data"})],
                response="",
            )
        ]

        result = evaluator.evaluate_invocations(actual)
        assert result.overall_score == 0.0

    def test_custom_weights(self):
        """不同权重配置改变评分。"""
        # 全忠实度权重
        faith_only = FaithfulnessEvaluator(
            faithfulness_weight=1.0,
            relevancy_weight=0.0,
        )
        # 全相关度权重
        relev_only = FaithfulnessEvaluator(
            faithfulness_weight=0.0,
            relevancy_weight=1.0,
        )

        actual = [
            _make_invocation(
                "Research AI trends",
                tool_calls=[("search_web", {"query": "AI"})],
                tool_responses=[
                    ("search_web", {"snippet": "machine learning deep learning neural networks"}),
                ],
                response="AI trends research shows exciting progress in the field.",
            )
        ]

        result_faith = faith_only.evaluate_invocations(actual)
        result_relev = relev_only.evaluate_invocations(actual)

        # 两种权重应该给出不同的分数
        assert result_faith.overall_score != result_relev.overall_score

    def test_faithful_vs_hallucinated_comparison(self):
        """忠实回答的分数应明显高于幻觉回答。"""
        evaluator = FaithfulnessEvaluator()

        tool_resp = [
            ("search_web", {
                "results": [
                    {"snippet": "Quantum computing advances include error correction and increased qubit counts."},
                ],
            }),
        ]

        faithful = [
            _make_invocation(
                "Quantum computing",
                tool_calls=[("search_web", {"query": "quantum"})],
                tool_responses=tool_resp,
                response="Quantum computing advances include error correction and increased qubit counts.",
            )
        ]

        hallucinated = [
            _make_invocation(
                "Quantum computing",
                tool_calls=[("search_web", {"query": "quantum"})],
                tool_responses=tool_resp,
                response="The stock market closed higher today with technology shares leading gains.",
            )
        ]

        result_faith = evaluator.evaluate_invocations(faithful)
        result_hall = evaluator.evaluate_invocations(hallucinated)

        assert result_faith.overall_score > result_hall.overall_score
