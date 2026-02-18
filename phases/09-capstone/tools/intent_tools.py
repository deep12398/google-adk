"""意图识别工具——规则引擎模式。

设计决策：
  - 使用正则规则而非 LLM 分类 → 零延迟、零成本、确定性
  - 输出置信度 → orchestrator 可在低置信度时用 LLM 判断覆盖
  - 意图历史写入 state → 可追踪用户行为模式
"""

import re

from google.adk.tools import ToolContext

# 6 种意图的匹配规则
INTENT_PATTERNS = {
    "search":       [r"\bfind\b", r"\bsearch\b", r"\blooking for\b", r"\bi need\b", r"\bsource\b"],
    "requirements": [r"\brequire", r"\bspec(ification)?s?\b", r"\bmust have\b", r"\bcriteria\b"],
    "qa":           [r"\bwhat is\b", r"\bexplain\b", r"\btell me about\b", r"\bhow does\b"],
    "quote":        [r"\bquote\b", r"\bpric(e|ing)\b", r"\bcost\b", r"\bhow much\b", r"\bbudget\b"],
    "compare":      [r"\bcompare\b", r"\bvs\.?\b", r"\bversus\b", r"\bbetter\b", r"\bwhich one\b"],
}


def classify_intent(user_message: str, tool_context: ToolContext) -> dict:
    """Classify user intent into: search, requirements, qa, quote, compare, or chitchat.

    Uses rule-based pattern matching for speed and determinism.
    The orchestrator can override with LLM judgment for ambiguous cases.

    Args:
        user_message: The user's message to classify.
    """
    msg = user_message.lower()

    # 计算每种意图的匹配分数
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, msg))
        if score > 0:
            scores[intent] = score

    # 选择最高分，无匹配则为 chitchat
    if not scores:
        classified, confidence = "chitchat", 0.5
    else:
        classified = max(scores, key=scores.get)
        confidence = min(scores[classified] / 3.0, 1.0)

    # 写入 state
    tool_context.state["temp:intent"] = classified
    tool_context.state["temp:intent_confidence"] = confidence

    # 追踪意图历史
    history = list(tool_context.state.get("intent_history", []))
    history.append(classified)
    tool_context.state["intent_history"] = history

    return {
        "intent": classified,
        "confidence": round(confidence, 2),
        "scores": scores,
    }
