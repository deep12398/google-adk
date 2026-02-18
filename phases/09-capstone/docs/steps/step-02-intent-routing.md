# Step 2: 意图识别 + 多 Agent 路由

## 教学目标

- **NEW** 意图识别模块：规则引擎 `classify_intent` 工具
- **Phase 03** sub_agents delegation：orchestrator 根据意图路由

## 学到什么

构建显式的意图分类层（不依赖 LLM 隐式路由），理解 orchestrator + sub_agents 的委托模式，
观察 `classify_intent → orchestrator routing → sub_agent execution` 的完整流程。

## 核心概念

```
classify_intent  — 规则引擎工具，将用户消息分类为 6 种意图
intent_agent     — 调用 classify_intent 的专用 Agent
orchestrator     — 根 Agent，根据意图将请求委托给 sub_agent
sub_agents       — LlmAgent 的 sub_agents 参数，声明可委托的子 Agent
```

## 意图类型

| 意图 | 含义 | 示例 |
|------|------|------|
| search | 搜索产品/供应商 | "Find stainless steel sheets" |
| requirements | 定义采购需求 | "I require ISO9001 certified materials" |
| qa | 提问/了解详情 | "What is the difference between 304 and 316?" |
| quote | 询价/报价 | "How much does aluminum cost?" |
| compare | 对比产品/供应商 | "Compare product A vs product B" |
| chitchat | 闲聊/兜底 | "Hello!" |

## 创建文件清单

```
新建:
  tools/intent_tools.py           # classify_intent 规则引擎
  agents/intent_agent.py          # 意图分类 Agent
  agents/orchestrator.py          # 根 Agent（路由协调）
  agents/chitchat_agent.py        # 闲聊兜底 Agent

修改:
  apps/app.py                     # 添加 STEP="2" → sourcing_orchestrator
```

## 代码实现

### tools/intent_tools.py

```python
"""意图识别工具——规则引擎模式。

设计决策：
  - 使用正则规则而非 LLM 分类 → 零延迟、零成本、确定性
  - 输出置信度 → orchestrator 可在低置信度时用 LLM 判断覆盖
  - 意图历史写入 state → 可追踪用户行为模式

对比 axon_ai：
  axon_ai 的 intelligent_requirements_agent 隐式地在 prompt 中做意图判断。
  我们将其显式化为独立工具，更可测试、可调试。
"""

import re
from google.adk.tools import ToolContext

# 6 种意图的匹配规则
INTENT_PATTERNS = {
    "search":       [r"\bfind\b", r"\bsearch\b", r"\blooking for\b", r"\bI need\b", r"\bsource\b"],
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
```

### agents/intent_agent.py

```python
"""意图分类 Agent——调用 classify_intent 并输出结果。

output_key="classified_intent" 将分类结果写入 state，
供 orchestrator 的 instruction 中通过 {classified_intent} 引用。
"""

from google.adk.agents.llm_agent import LlmAgent
from tools.intent_tools import classify_intent

intent_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="intent_agent",
    description="Classifies user intent before routing to specialized agents.",
    instruction=(
        "You are an intent classifier for a sourcing assistant.\n\n"
        "1. Call classify_intent with the user's EXACT message.\n"
        "2. If confidence < 0.5, use your judgment to refine.\n"
        "3. Report the classified intent.\n"
    ),
    tools=[classify_intent],
    output_key="classified_intent",
)
```

### agents/chitchat_agent.py

```python
"""闲聊兜底 Agent——处理非采购相关的对话。"""

from google.adk.agents.llm_agent import LlmAgent

chitchat_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="chitchat_agent",
    description="Handles casual conversation and general questions.",
    instruction=(
        "You are a friendly sourcing assistant.\n"
        "Handle casual conversation briefly.\n"
        "Remind the user you can help with:\n"
        "- Searching products and suppliers\n"
        "- Getting price quotes\n"
        "- Comparing options\n"
    ),
)
```

### agents/orchestrator.py（Step 2 版本）

```python
"""Sourcing Orchestrator——根 Agent。

Step 2 版本：3 个 sub_agents（intent, catalog_search, chitchat）。
后续 Step 会逐步添加更多 sub_agents。

关键模式：
  - sub_agents 列表声明可委托的子 Agent
  - instruction 中定义路由规则
  - LLM 根据 instruction 决定委托给哪个 sub_agent
"""

from google.adk.agents.llm_agent import LlmAgent
from agents.intent_agent import intent_agent
from agents.catalog_search_agent import catalog_search_agent
from agents.chitchat_agent import chitchat_agent

sourcing_orchestrator = LlmAgent(
    model="gemini-2.0-flash",
    name="sourcing_orchestrator",
    description="Routes user requests to the appropriate sourcing sub-agent.",
    instruction=(
        "You are the sourcing assistant orchestrator.\n\n"
        "## Routing Rules\n"
        "1. FIRST: delegate to intent_agent to classify the user's intent.\n"
        "2. Based on classified intent:\n"
        "   - 'search' → delegate to catalog_search_agent\n"
        "   - 'chitchat' → delegate to chitchat_agent\n"
        "   - other intents → handle directly (more agents coming in later steps)\n\n"
        "3. Always acknowledge the intent classification before routing.\n"
    ),
    sub_agents=[intent_agent, catalog_search_agent, chitchat_agent],
)
```

### apps/app.py 修改

在 `ROOT_AGENTS` 字典中添加：

```python
from agents.orchestrator import sourcing_orchestrator  # noqa: E402

ROOT_AGENTS = {
    "1": catalog_search_agent,
    "2": sourcing_orchestrator,
}
```

## 验证

```bash
cd phases/09-capstone

# 搜索意图 → 路由到 catalog_search_agent
STEP=2 PROMPT="Find me aluminum sheets for electronics" python apps/main.py

# 闲聊意图 → 路由到 chitchat_agent
STEP=2 PROMPT="Hello, how are you?" python apps/main.py

# 报价意图 → orchestrator 直接处理（还没有 quote_agent）
STEP=2 PROMPT="How much does steel cost?" python apps/main.py
```

## 你应该理解的

1. `sub_agents` 是 LlmAgent 的参数，声明该 Agent 可以委托给哪些子 Agent
2. LLM 根据 `instruction` 中的路由规则和子 Agent 的 `description` 来决定委托
3. `classify_intent` 是规则引擎，确定性输出 → 可单元测试、零 LLM 成本
4. `output_key` 将 Agent 输出写入 state，供后续 Agent 读取
5. 意图识别与 LLM 路由是互补的：规则引擎处理明确意图，LLM 处理模糊情况
