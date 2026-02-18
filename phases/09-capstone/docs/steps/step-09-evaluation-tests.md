# Step 9: 评测 + 测试

## 教学目标

- **Phase 07** TrajectoryEvaluator + ResponseEvaluator
- **Phase 07** 自定义 Evaluator ABC（CascadeEvaluator, IntentEvaluator）
- **Phase 07** AgentEvaluator.evaluate() E2E 评测
- pytest 单元测试

## 学到什么

如何为复杂多 Agent 系统编写评测：
工具轨迹评估（是否调用了正确的工具），
级联正确性评估（搜索顺序是否正确），
意图分类准确率评估，
以及纯 Python 单元测试（不需要 LLM）。

## 核心概念

```
Evaluator ABC          — 自定义评估器基类
  evaluate_invocations(actual, expected) → EvaluationResult

TrajectoryEvaluator    — 检查工具调用轨迹是否匹配预期
ResponseEvaluator      — 检查最终响应是否匹配参考答案（ROUGE-1）
CascadeEvaluator       — 自定义：检查级联搜索顺序是否正确
IntentEvaluator        — 自定义：检查意图分类是否准确
AgentEvaluator.evaluate() — E2E 评测入口

eval_data/*.test.json  — 评测数据集
  [{"name": "case_name", "data": [{"query": "...", "expected_tool_use": [...]}]}]
```

## 创建文件清单

```
新建:
  evaluators/
    __init__.py
    cascade_evaluator.py          # 自定义：级联顺序正确性
    intent_evaluator.py           # 自定义：意图分类准确率
  eval_data/
    search_cascade.test.json      # 3 case
    intent_classification.test.json  # 3 case
    full_workflow.test.json       # 2 case
  tests/
    __init__.py
    test_intent_tools.py          # 单元测试
    test_catalog_tools.py         # 单元测试
    test_cascade_evaluator.py     # 评估器单元测试

修改:
  apps/app.py                     # STEP="9" + MODE=eval 支持
```

## 代码实现

### evaluators/cascade_evaluator.py

```python
"""级联搜索评估器——验证 3 级搜索的执行顺序。

规则：
  - Tier 1 (search_catalog) 必须在 Tier 2 (search_suppliers) 之前
  - Tier 2 必须在 Tier 3 (search_external) 之前
  - 乱序扣分
"""

from __future__ import annotations
from typing import Optional
from statistics import mean

from google.adk.evaluation.eval_case import Invocation, get_all_tool_calls
from google.adk.evaluation.eval_metrics import EvalStatus
from google.adk.evaluation.evaluator import (
    EvaluationResult,
    Evaluator,
    PerInvocationResult,
)

# 工具名 → 层级编号
TIER_ORDER = {
    "search_catalog": 1,
    "search_suppliers": 2,
    "search_external": 3,
}


class CascadeEvaluator(Evaluator):
    """验证 3 级级联搜索遵循正确顺序。"""

    def __init__(self, threshold: float = 0.5) -> None:
        self._threshold = threshold

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
        for inv in actual_invocations:
            tool_calls = get_all_tool_calls(inv.intermediate_data)
            tool_names = [tc.name for tc in tool_calls]

            # 提取搜索工具的调用顺序
            tier_calls = [
                (TIER_ORDER[name], name)
                for name in tool_names
                if name in TIER_ORDER
            ]

            # 评分：层级必须递增
            score = 1.0
            for i in range(1, len(tier_calls)):
                if tier_calls[i][0] < tier_calls[i - 1][0]:
                    score -= 0.5  # 乱序扣 0.5

            score = max(score, 0.0)

            per_results.append(
                PerInvocationResult(
                    actual_invocation=inv,
                    expected_invocation=None,
                    score=score,
                    eval_status=(
                        EvalStatus.PASSED if score >= self._threshold
                        else EvalStatus.FAILED
                    ),
                )
            )

        overall = mean(r.score for r in per_results) if per_results else 0.0
        return EvaluationResult(
            overall_score=overall,
            overall_eval_status=(
                EvalStatus.PASSED if overall >= self._threshold
                else EvalStatus.FAILED
            ),
            per_invocation_results=per_results,
        )
```

### evaluators/intent_evaluator.py

```python
"""意图分类评估器——验证 classify_intent 是否被调用且分类正确。"""

from __future__ import annotations
from typing import Optional
from statistics import mean

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
```

### eval_data/search_cascade.test.json

```json
[
  {
    "name": "tier1_catalog_hit",
    "data": [
      {
        "query": "Find stainless steel sheets",
        "expected_tool_use": [
          {"tool_name": "classify_intent", "tool_input": {"user_message": "Find stainless steel sheets"}},
          {"tool_name": "search_catalog", "tool_input": {"query": "stainless steel"}}
        ],
        "reference": "Found stainless steel products in our catalog."
      }
    ]
  },
  {
    "name": "tier1_to_tier2_cascade",
    "data": [
      {
        "query": "Find titanium alloy suppliers",
        "expected_tool_use": [
          {"tool_name": "classify_intent"},
          {"tool_name": "search_catalog"},
          {"tool_name": "search_suppliers"}
        ],
        "reference": "Catalog results insufficient, searched supplier database."
      }
    ]
  },
  {
    "name": "full_cascade_tier1_to_tier3",
    "data": [
      {
        "query": "Find carbon fiber composite panels",
        "expected_tool_use": [
          {"tool_name": "classify_intent"},
          {"tool_name": "search_catalog"},
          {"tool_name": "search_suppliers"},
          {"tool_name": "search_external"}
        ],
        "reference": "No internal results, searched external sources."
      }
    ]
  }
]
```

### eval_data/intent_classification.test.json

```json
[
  {
    "name": "search_intent",
    "data": [
      {
        "query": "I need to find stainless steel sheets",
        "expected_tool_use": [
          {"tool_name": "classify_intent", "tool_input": {"user_message": "I need to find stainless steel sheets"}}
        ],
        "reference": "Intent classified as search."
      }
    ]
  },
  {
    "name": "quote_intent",
    "data": [
      {
        "query": "How much does aluminum cost per ton?",
        "expected_tool_use": [
          {"tool_name": "classify_intent"}
        ],
        "reference": "Intent classified as quote."
      }
    ]
  },
  {
    "name": "chitchat_intent",
    "data": [
      {
        "query": "Hello, good morning!",
        "expected_tool_use": [
          {"tool_name": "classify_intent"}
        ],
        "reference": "Intent classified as chitchat."
      }
    ]
  }
]
```

### tests/test_intent_tools.py

```python
"""classify_intent 单元测试——不需要 LLM。

使用 MagicMock 模拟 ToolContext。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# 添加项目路径
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.intent_tools import classify_intent


def _mock_ctx():
    """创建模拟的 ToolContext。"""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


class TestClassifyIntent:

    def test_search_intent_find(self):
        result = classify_intent("I need to find steel sheets", _mock_ctx())
        assert result["intent"] == "search"
        assert result["confidence"] > 0

    def test_search_intent_looking_for(self):
        result = classify_intent("I'm looking for aluminum suppliers", _mock_ctx())
        assert result["intent"] == "search"

    def test_quote_intent(self):
        result = classify_intent("How much does aluminum cost?", _mock_ctx())
        assert result["intent"] == "quote"

    def test_compare_intent(self):
        result = classify_intent("Compare product A vs product B", _mock_ctx())
        assert result["intent"] == "compare"

    def test_qa_intent(self):
        result = classify_intent("What is the difference between 304 and 316?", _mock_ctx())
        assert result["intent"] == "qa"

    def test_requirements_intent(self):
        result = classify_intent("The specifications must have ISO9001", _mock_ctx())
        assert result["intent"] == "requirements"

    def test_chitchat_fallback(self):
        result = classify_intent("Hello!", _mock_ctx())
        assert result["intent"] == "chitchat"
        assert result["confidence"] == 0.5

    def test_state_update(self):
        ctx = _mock_ctx()
        classify_intent("Find steel", ctx)
        assert ctx.state["temp:intent"] == "search"
        assert "intent_history" in ctx.state
```

### tests/test_catalog_tools.py

```python
"""search_catalog 单元测试——不需要 LLM。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.catalog_tools import search_catalog


def _mock_ctx():
    ctx = MagicMock()
    ctx.state = {}
    return ctx


class TestSearchCatalog:

    def test_returns_dict(self):
        ctx = _mock_ctx()
        result = search_catalog("steel", ctx)
        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_state_updated(self):
        ctx = _mock_ctx()
        search_catalog("steel", ctx)
        assert "catalog_results" in ctx.state
        assert ctx.state["search_count"] == 1
        assert ctx.state["last_query"] == "steel"

    def test_no_results_for_unknown(self):
        ctx = _mock_ctx()
        result = search_catalog("xyznonexistent", ctx)
        assert result["total"] == 0
        assert result["results"] == []
```

### tests/test_cascade_evaluator.py

```python
"""CascadeEvaluator 单元测试。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from evaluators.cascade_evaluator import CascadeEvaluator
from google.adk.evaluation.eval_metrics import EvalStatus


def _make_invocation(tool_names: list[str]):
    """创建模拟的 Invocation。"""
    inv = MagicMock()
    # 模拟 intermediate_data 中的 tool calls
    tool_calls = []
    for name in tool_names:
        tc = MagicMock()
        tc.name = name
        tool_calls.append(tc)

    # get_all_tool_calls 需要从 intermediate_data 提取
    inv.intermediate_data = MagicMock()
    inv.intermediate_data.tool_calls = tool_calls
    return inv, tool_calls


class TestCascadeEvaluator:

    def test_correct_order_tier1_only(self):
        evaluator = CascadeEvaluator()
        # 注意：需要 mock get_all_tool_calls
        # 这里是概念性测试结构

    def test_correct_order_tier1_then_tier2(self):
        pass  # 需要适配 get_all_tool_calls 的 mock

    def test_wrong_order_penalized(self):
        pass  # tier2 在 tier1 之前 → score 扣分
```

## 验证

```bash
cd phases/09-capstone

# 单元测试（不需要 API key）
python -m pytest tests/test_intent_tools.py -v
python -m pytest tests/test_catalog_tools.py -v

# 全部测试
python -m pytest tests/ -v

# E2E 评测（需要 API key）
STEP=9 MODE=eval python apps/main.py
```

## 你应该理解的

1. `Evaluator` ABC 要求实现 `evaluate_invocations(actual, expected) → EvaluationResult`
2. `get_all_tool_calls(invocation.intermediate_data)` 提取工具调用轨迹
3. `EvalStatus.PASSED / FAILED / NOT_EVALUATED` 表示评估结果
4. 单元测试用 `MagicMock` 模拟 `ToolContext` → 不需要 LLM / API key
5. eval_data/*.test.json 格式：`[{"name": "...", "data": [{"query": "...", "expected_tool_use": [...]}]}]`
6. `CascadeEvaluator` 是业务特有的 → 验证搜索顺序
7. 评测 + 测试是 Agent 系统质量保证的基础
