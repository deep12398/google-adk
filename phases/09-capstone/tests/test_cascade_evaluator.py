"""CascadeEvaluator 单元测试。

用真实的 Invocation / IntermediateData / FunctionCall 对象，
验证评分逻辑：正确顺序得满分，乱序扣分。
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from google.genai import types

from evaluators.cascade_evaluator import CascadeEvaluator
from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalStatus


def _make_invocation(tool_names: list[str]) -> Invocation:
    """创建带工具调用轨迹的 Invocation。"""
    tool_uses = [
        types.FunctionCall(name=name, args={}) for name in tool_names
    ]
    return Invocation(
        user_content=types.Content(parts=[types.Part(text="test")], role="user"),
        intermediate_data=IntermediateData(tool_uses=tool_uses),
    )


class TestCascadeEvaluator:

    def test_correct_order_tier1_only(self):
        """只有 Tier 1 → 满分。"""
        inv = _make_invocation(["search_catalog"])
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([inv])
        assert result.overall_score == 1.0
        assert result.overall_eval_status == EvalStatus.PASSED

    def test_correct_order_tier1_then_tier2(self):
        """Tier 1 → Tier 2 正确顺序 → 满分。"""
        inv = _make_invocation(["search_catalog", "search_suppliers"])
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([inv])
        assert result.overall_score == 1.0

    def test_correct_order_full_cascade(self):
        """Tier 1 → 2 → 3 完整级联 → 满分。"""
        inv = _make_invocation(["search_catalog", "search_suppliers", "search_external"])
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([inv])
        assert result.overall_score == 1.0

    def test_wrong_order_penalized(self):
        """Tier 2 在 Tier 1 之前 → 扣分。"""
        inv = _make_invocation(["search_suppliers", "search_catalog"])
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([inv])
        assert result.overall_score == 0.5

    def test_completely_reversed_fails(self):
        """Tier 3 → 2 → 1 完全倒序 → 0 分。"""
        inv = _make_invocation(["search_external", "search_suppliers", "search_catalog"])
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([inv])
        assert result.overall_score == 0.0
        assert result.overall_eval_status == EvalStatus.FAILED

    def test_non_search_tools_ignored(self):
        """非搜索工具不影响评分。"""
        inv = _make_invocation(["classify_intent", "search_catalog", "compare_products"])
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([inv])
        assert result.overall_score == 1.0

    def test_empty_invocations(self):
        """空 invocations → NOT_EVALUATED。"""
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([])
        assert result.overall_eval_status == EvalStatus.NOT_EVALUATED

    def test_multiple_invocations_averaged(self):
        """多个 invocations 取平均分。"""
        inv1 = _make_invocation(["search_catalog", "search_suppliers"])  # 正确 → 1.0
        inv2 = _make_invocation(["search_suppliers", "search_catalog"])  # 乱序 → 0.5
        evaluator = CascadeEvaluator()
        result = evaluator.evaluate_invocations([inv1, inv2])
        assert result.overall_score == 0.75
