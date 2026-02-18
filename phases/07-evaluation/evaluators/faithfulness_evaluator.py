"""忠实度评估器——检查 Agent 回答是否基于工具返回的内容。

灵感来自 n6-agent 的 RAGAS Faithfulness 指标：
  Agent 不应该"瞎编"——它的回答应该可以追溯到工具返回的信息。

实现思路（不依赖 LLM Judge）：
  1. 从 Invocation 中提取工具返回的所有内容（tool_responses）
  2. 从 final_response 中提取 Agent 的最终回答
  3. 计算回答中有多少关键词可以在工具输出中找到（忠实度）
  4. 同时计算工具输出中有多少内容被回答引用（覆盖率）

两个维度：
  - faithfulness_score：回答的关键词中，多少比例出现在工具输出中（grounded）
  - relevancy_score：回答与用户问题的关键词重叠率

参考：n6-agent-be/src/ai_engine/tools/langsmith/rag_evaluator.py
  - calculate_faithfulness(): answer 关键词在 context 中的覆盖率
  - calculate_answer_relevancy(): answer 关键词与 query 的重叠率
"""

from __future__ import annotations

import re
from statistics import mean
from typing import Optional

from google.adk.evaluation.eval_case import (
    Invocation,
    get_all_tool_responses,
)
from google.adk.evaluation.eval_metrics import EvalStatus
from google.adk.evaluation.evaluator import (
    EvaluationResult,
    Evaluator,
    PerInvocationResult,
)


# ---------- 文本处理 ----------

# 英文停用词（简化版）
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "my", "your", "his", "its", "our", "their", "this", "that", "these",
    "those", "what", "which", "who", "whom", "where", "when", "why", "how",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "about", "between", "through", "during", "before", "after",
    "and", "but", "or", "not", "no", "so", "if", "then", "than", "too",
    "very", "just", "also", "more", "most", "some", "any", "all", "each",
})


def _tokenize(text: str) -> set[str]:
    """提取有意义的关键词（去停用词、去标点、小写化）。"""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def _extract_text(content) -> str:
    """从 Content 对象提取纯文本。"""
    if content is None:
        return ""
    if hasattr(content, "parts") and content.parts:
        return " ".join(
            part.text for part in content.parts
            if hasattr(part, "text") and part.text
        )
    return ""


def _extract_tool_output_text(intermediate_data) -> str:
    """从工具返回中提取所有文本内容。

    tool_responses 是 list[FunctionResponse]，每个有 response: dict。
    我们递归地把 dict 中所有字符串值拼接起来。
    """
    tool_responses = get_all_tool_responses(intermediate_data)
    texts = []
    for resp in tool_responses:
        if resp.response:
            texts.append(_flatten_dict_values(resp.response))
    return " ".join(texts)


def _flatten_dict_values(d: dict) -> str:
    """递归提取 dict 中的所有字符串值。"""
    parts = []
    for v in d.values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            parts.append(_flatten_dict_values(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(_flatten_dict_values(item))
    return " ".join(parts)


# ---------- 评估器 ----------


class FaithfulnessEvaluator(Evaluator):
    """忠实度评估器。

    检查两个维度（可配置权重）：

    1. faithfulness（忠实度）：
       Agent 回答中的关键词，有多少比例能在工具输出中找到？
       分数高 = 回答有据可依，不是瞎编的。

    2. relevancy（相关度）：
       Agent 回答中的关键词，有多少比例与用户问题相关？
       分数高 = 回答紧扣主题，没有跑题。

    用法：
        evaluator = FaithfulnessEvaluator(
            faithfulness_weight=0.6,
            relevancy_weight=0.4,
            threshold=0.3,
        )
        result = evaluator.evaluate_invocations(actual, expected)
    """

    def __init__(
        self,
        faithfulness_weight: float = 0.6,
        relevancy_weight: float = 0.4,
        threshold: float = 0.3,
    ):
        self._faith_w = faithfulness_weight
        self._relev_w = relevancy_weight
        self._threshold = threshold

    @staticmethod
    def _calc_faithfulness(response_text: str, tool_output_text: str) -> float:
        """回答关键词在工具输出中的覆盖率。"""
        response_words = _tokenize(response_text)
        tool_words = _tokenize(tool_output_text)

        if not response_words:
            return 0.0
        if not tool_words:
            # 没有工具输出，无法判断忠实度
            return 0.0

        grounded = response_words & tool_words
        return len(grounded) / len(response_words)

    @staticmethod
    def _calc_relevancy(response_text: str, query_text: str) -> float:
        """回答关键词与用户问题的重叠率。"""
        response_words = _tokenize(response_text)
        query_words = _tokenize(query_text)

        if not query_words:
            return 0.0
        if not response_words:
            return 0.0

        overlap = response_words & query_words
        return len(overlap) / len(query_words)

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

        per_results: list[PerInvocationResult] = []

        for i, inv in enumerate(actual_invocations):
            response_text = _extract_text(inv.final_response)
            query_text = _extract_text(inv.user_content)
            tool_output_text = _extract_tool_output_text(inv.intermediate_data)

            faith = self._calc_faithfulness(response_text, tool_output_text)
            relev = self._calc_relevancy(response_text, query_text)
            score = round(faith * self._faith_w + relev * self._relev_w, 3)

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
                        EvalStatus.PASSED
                        if score >= self._threshold
                        else EvalStatus.FAILED
                    ),
                )
            )

        overall = round(
            mean(r.score for r in per_results if r.score is not None), 3
        )
        return EvaluationResult(
            overall_score=overall,
            overall_eval_status=(
                EvalStatus.PASSED
                if overall >= self._threshold
                else EvalStatus.FAILED
            ),
            per_invocation_results=per_results,
        )
