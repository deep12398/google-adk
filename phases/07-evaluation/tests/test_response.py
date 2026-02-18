"""响应匹配评测——ResponseEvaluator (ROUGE) 测试。

ResponseEvaluator 支持两种 metric：
  - response_match_score：ROUGE-1 文本相似度（0~1）
  - response_evaluation_score：Vertex AI 评估（需要 API，1~5）

本文件只测 response_match_score（不需要外部 API）。
ROUGE-1 计算 unigram 重叠率，用于衡量 actual 与 expected 的文本相似程度。
"""

import pytest
from google.genai import types

from google.adk.evaluation.eval_case import Invocation
from google.adk.evaluation.eval_metrics import EvalStatus
from google.adk.evaluation.response_evaluator import ResponseEvaluator


# ---------- 辅助函数 ----------


def _make_invocation(query: str, response: str) -> Invocation:
    """构造只有 user_content 和 final_response 的 Invocation。"""
    return Invocation(
        user_content=types.Content(
            parts=[types.Part.from_text(text=query)],
            role="user",
        ),
        final_response=types.Content(
            parts=[types.Part.from_text(text=response)],
            role="model",
        ),
    )


# ---------- 测试用例 ----------


class TestResponseMatch:
    """response_match_score（ROUGE-1）测试。"""

    def test_identical_response(self):
        """完全相同的文本 → 接近 1.0。"""
        evaluator = ResponseEvaluator(
            threshold=0.8,
            metric_name="response_match_score",
        )

        text = "AI trends include automation and scalability."
        actual = [_make_invocation("Research AI", text)]
        expected = [_make_invocation("Research AI", text)]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score is not None
        assert result.overall_score >= 0.9  # 相同文本应接近 1.0

    def test_similar_response(self):
        """内容相似但措辞不同 → 中等分数。"""
        evaluator = ResponseEvaluator(
            threshold=0.3,
            metric_name="response_match_score",
        )

        actual = [
            _make_invocation(
                "Research AI",
                "Recent AI trends show progress in automation, scalability, and integration of systems.",
            )
        ]
        expected = [
            _make_invocation(
                "Research AI",
                "AI trends include automation, scalability, and integration. Major progress has been made.",
            )
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score is not None
        assert result.overall_score > 0.3  # 相似内容应有一定分数

    def test_completely_different_response(self):
        """完全不相关的文本 → 低分。"""
        evaluator = ResponseEvaluator(
            threshold=0.8,
            metric_name="response_match_score",
        )

        actual = [
            _make_invocation(
                "Research AI",
                "The weather today is sunny with clear skies.",
            )
        ]
        expected = [
            _make_invocation(
                "Research AI",
                "AI trends include deep learning, transformers, and large language models.",
            )
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_score is not None
        assert result.overall_score < 0.5  # 不相关文本应低分

    def test_threshold_determines_status(self):
        """阈值决定 PASSED / FAILED 状态。"""
        # 高阈值 → 不完全匹配会 FAIL
        evaluator = ResponseEvaluator(
            threshold=0.99,
            metric_name="response_match_score",
        )

        actual = [
            _make_invocation("Q", "AI is great for automation.")
        ]
        expected = [
            _make_invocation("Q", "AI is useful for various applications.")
        ]

        result = evaluator.evaluate_invocations(actual, expected)
        assert result.overall_eval_status == EvalStatus.FAILED
