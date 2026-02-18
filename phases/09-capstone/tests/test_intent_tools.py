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
