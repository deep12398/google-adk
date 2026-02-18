# 1.7 评估与回归

## 编写

Phase 03-06 构建了功能完整的 Agent 系统，但从未验证过"Agent 的输出是否正确"。真实应用中，Agent 的行为可能因 prompt 修改、模型升级、工具变更而退化。本阶段引入 ADK 的评测框架，建立可重复的回归测试。

**核心问题：** 你怎么知道 Agent 还在正确工作？

```
修改 prompt → 工具调用序列变了 → 输出质量下降 → 没有评测 → 线上出问题才发现
                                                ↓ 有了评测
                                          每次改动 → 跑评测集 → 立即发现退化
```

| 序号 | 能力 | ADK 载体 | 本阶段示例 |
|:---:|------|----------|-----------:|
| 1 | 评测数据格式 | `EvalSet` / `EvalCase` / `Invocation` | `eval_data/research.test.json` |
| 2 | 工具轨迹评估 | `TrajectoryEvaluator`（比较工具调用序列） | `tests/test_trajectory.py` |
| 3 | 响应匹配评估 | `ResponseEvaluator`（ROUGE 文本相似度） | `tests/test_response.py` |
| 4 | 自定义评估器 | 继承 `Evaluator` ABC | `evaluators/custom_evaluator.py` |
| 5 | 端到端评测管线 | `AgentEvaluator.evaluate()` | `tests/test_e2e.py` |
| 6 | 忠实度评估 | 自定义 `FaithfulnessEvaluator` | `evaluators/faithfulness_evaluator.py` |
| 7 | 复合评分 | 自定义 `CompositeEvaluator` | `evaluators/composite_evaluator.py` |
| 8 | 结构化报告 | 自定义 `MetricsReporter` | `evaluators/metrics_reporter.py` |

---

## 讲解

### 一、评测数据格式

ADK 评测的核心数据结构：

```
EvalSet（评测集）
  └── eval_cases: list[EvalCase]（评测用例）
        └── conversation: list[Invocation]（对话轮次）
              ├── user_content: Content（用户输入）
              ├── final_response: Content（期望的参考响应）
              └── intermediate_data: IntermediateData
                    ├── tool_uses: list[FunctionCall]（期望的工具调用）
                    └── tool_responses: list[FunctionResponse]（工具返回内容）
```

**JSON 格式（legacy 格式，ADK 自动识别）：**

```json
[
  {
    "name": "search_ai_trends",
    "data": [
      {
        "query": "Research the latest AI trends",
        "expected_tool_use": [
          {"tool_name": "search_web", "tool_input": {"query": "latest AI trends"}}
        ],
        "reference": "Based on my research, AI trends include..."
      }
    ]
  }
]
```

每个 `data` 条目对应一轮对话（一个 `Invocation`）：
- `query` → `user_content`
- `expected_tool_use` → `intermediate_data.tool_uses`
- `reference` → `final_response`

---

### 二、TrajectoryEvaluator（工具轨迹评估）

比较 Agent 实际调用的工具序列与期望序列。

**三种匹配模式：**

| 模式 | 含义 | 示例 |
|------|------|------|
| `EXACT` | 完全匹配，不允许多余或缺少 | expected=[A,B], actual=[A,B] ✓ |
| `IN_ORDER` | 顺序匹配，允许有额外调用 | expected=[A,B], actual=[A,C,B] ✓ |
| `ANY_ORDER` | 存在即可，不管顺序 | expected=[A,B], actual=[B,A] ✓ |

```python
from google.adk.evaluation.trajectory_evaluator import (
    TrajectoryEvaluator, ToolTrajectoryCriterion,
)
from google.adk.evaluation.eval_metrics import EvalMetric

evaluator = TrajectoryEvaluator(
    eval_metric=EvalMetric(
        metric_name="tool_trajectory_avg_score",
        threshold=1.0,
        criterion=ToolTrajectoryCriterion(
            threshold=1.0,
            match_type=ToolTrajectoryCriterion.MatchType.EXACT,
        ),
    ),
)

result = evaluator.evaluate_invocations(actual, expected)
# result.overall_score: 0.0 ~ 1.0
# result.overall_eval_status: PASSED / FAILED
```

**底层机制：** TrajectoryEvaluator 对每个 Invocation 逐个比较，匹配返回 1.0，不匹配返回 0.0，最终取平均分。

---

### 三、ResponseEvaluator（响应匹配评估）

比较 Agent 的实际响应与参考响应的文本相似度。

```python
from google.adk.evaluation.response_evaluator import ResponseEvaluator

evaluator = ResponseEvaluator(
    threshold=0.5,
    metric_name="response_match_score",  # ROUGE-1
)

result = evaluator.evaluate_invocations(actual, expected)
# result.overall_score: 0.0 ~ 1.0（ROUGE-1 unigram 重叠率）
```

**两种 metric：**

| metric_name | 方法 | 分数范围 | 需要 API |
|---|---|---|---|
| `response_match_score` | ROUGE-1（unigram 重叠） | 0~1 | 否 |
| `response_evaluation_score` | Vertex AI Coherence 评估 | 1~5 | 是 |

---

### 四、自定义评估器

继承 `Evaluator` ABC，实现 `evaluate_invocations()` 方法：

```python
from google.adk.evaluation.evaluator import Evaluator, EvaluationResult, PerInvocationResult

class QualityEvaluator(Evaluator):
    def evaluate_invocations(self, actual, expected=None) -> EvaluationResult:
        per_results = []
        for inv in actual:
            # 自定义评分逻辑
            tool_calls = get_all_tool_calls(inv.intermediate_data)
            has_search = any(tc.name == "search_web" for tc in tool_calls)
            score = 1.0 if has_search else 0.0

            per_results.append(PerInvocationResult(
                actual_invocation=inv, score=score, eval_status=...
            ))

        return EvaluationResult(
            overall_score=mean(r.score for r in per_results),
            per_invocation_results=per_results,
        )
```

**Evaluator ABC 接口：**
- 输入：`actual_invocations`（Agent 实际运行结果）+ `expected_invocations`（参考/可选）
- 输出：`EvaluationResult`（overall_score + per_invocation_results）
- 所有内置评估器和自定义评估器都实现同一接口

---

### 五、端到端评测管线

`AgentEvaluator.evaluate()` 串联整个流程：

```python
from google.adk.evaluation import AgentEvaluator

await AgentEvaluator.evaluate(
    agent_module="agents.research_agent",        # 被测 Agent 模块
    eval_dataset_file_path_or_dir="eval_data/",  # .test.json 目录
    num_runs=2,                                  # 每个用例运行几次
    agent_name="research_agent",                 # Agent 名称
    print_detailed_results=True,                 # 打印详细结果
)
```

**执行流程：**
1. 递归查找 `.test.json` 文件
2. 解析为 `EvalSet` / `EvalCase`
3. 读取同目录的 `test_config.json`（评测指标 + 阈值）
4. 对每个 EvalCase 运行 Agent（num_runs 次）
5. 用配置的 Evaluator 评估
6. Assert 所有指标达到阈值

---

### 六、FaithfulnessEvaluator（忠实度评估）

**为什么需要忠实度？** 一个 Agent 可能调了正确的工具、回答了足够长的文本，但内容完全是"瞎编的"——和工具返回的信息无关。这就是幻觉（Hallucination）。

灵感来自 n6-agent 的 RAGAS Faithfulness 指标。实现思路：

```python
faithfulness = Agent 回答中的关键词能在工具输出中找到的比例
relevancy = Agent 回答中的关键词与用户问题的重叠比例
score = faithfulness * 0.6 + relevancy * 0.4
```

**关键示例（来自实际运行）：**

```
Hallucinated Agent:
  trajectory  = 1.0   ← 调了正确的工具 ✓
  quality     = 1.0   ← 回答格式没问题 ✓
  faithfulness = 0.0  ← 但回答和工具输出完全无关！✗
  综合分 = 0.600       ← 如果没有忠实度检查，这个 Agent "看起来完美"
```

工具返回的是 AI 趋势内容，但 Agent 回答了天气预报——只有忠实度评估能抓到这个问题。

---

### 七、CompositeEvaluator（复合评分）

单一指标无法全面衡量 Agent 质量。CompositeEvaluator 加权组合多个评估器：

```python
composite = CompositeEvaluator(
    evaluators={
        "trajectory":   (TrajectoryEvaluator(threshold=0.8), 0.3),  # 30% 权重
        "faithfulness": (FaithfulnessEvaluator(),             0.4),  # 40% 权重
        "quality":      (QualityEvaluator(),                  0.3),  # 30% 权重
    },
    threshold=0.5,
)

result = composite.evaluate_invocations(actual, expected)
composite.print_report()
# Overall: 0.987
# Dimensions:
#   trajectory      score=1.000  weight=30.0%  weighted=0.300
#   faithfulness    score=0.968  weight=40.0%  weighted=0.387
#   quality         score=1.000  weight=30.0%  weighted=0.300
```

类似 n6-agent 的 `overall_rag_score = retrieval * 0.4 + generation * 0.6`。

---

### 八、MetricsReporter（结构化报告）

评测结果需要持久化，才能做历史对比和趋势分析。MetricsReporter 生成 JSON 报告：

```python
reporter = MetricsReporter(report_dir="./reports")

reporter.add_result("case_1", {"trajectory": 1.0, "faithfulness": 0.8}, "PASSED")
reporter.add_result("case_2", {"trajectory": 0.0, "faithfulness": 0.3}, "FAILED")

reporter.print_summary()
reporter.save_report()  # → reports/eval_report_20260216_001421.json
```

报告格式（类似 n6-agent 的 `langsmith_metrics_evaluation_report.json`）：

```json
{
  "evaluation_summary": {
    "timestamp": "2026-02-16T00:14:21",
    "total_cases": 3,
    "passed": 2,
    "failed": 1,
    "pass_rate": 0.667,
    "average_metrics": {
      "trajectory":   {"avg": 0.667, "min": 0.0, "max": 1.0},
      "faithfulness": {"avg": 0.323, "min": 0.0, "max": 0.968}
    }
  },
  "detailed_results": [...]
}
```

---

## 小结

1. **评测数据 = 输入 + 期望输出 + 期望工具调用。** `.test.json` 文件定义评测集，JSON 格式。
2. **TrajectoryEvaluator 验证"做了什么"。** 三种匹配模式比较工具调用序列。
3. **ResponseEvaluator 验证"说了什么"。** ROUGE-1 文本相似度，衡量响应质量。
4. **FaithfulnessEvaluator 验证"有没有瞎编"。** 回答是否基于工具返回的真实内容，防止幻觉。
5. **CompositeEvaluator 加权组合。** 多维度评分 + 权重 = 一个综合分数，类似 RAGAS overall_score。
6. **MetricsReporter 持久化报告。** JSON 格式，avg/min/max 统计，支持历史对比和回归检测。
7. **自定义评估器无限扩展。** 继承 Evaluator ABC，实现任意评测逻辑。
8. **AgentEvaluator 串联端到端。** 加载数据 → 运行 Agent → 评估 → Assert，一行代码完成回归测试。

---

## 代码布局

```
phases/07-evaluation/
  tools/
    search_tool.py              # search_web 模拟工具（被测 Agent 使用）
  agents/
    research_agent.py           # 被测 Agent（search_web + summarize）
  evaluators/
    custom_evaluator.py         # QualityEvaluator（工具调用检查 + 响应长度检查）
    faithfulness_evaluator.py   # FaithfulnessEvaluator（忠实度 + 相关度）
    composite_evaluator.py      # CompositeEvaluator（加权复合评分）
    metrics_reporter.py         # MetricsReporter（JSON 结构化报告）
  eval_data/
    research.test.json          # 单轮评测集（3 个用例）
    multi_turn.test.json        # 多轮对话评测集（1 个 2 轮用例）
    test_config.json            # 评测指标配置（阈值）
  tests/
    test_trajectory.py          # TrajectoryEvaluator 单元测试（三种匹配模式）
    test_response.py            # ResponseEvaluator 单元测试（ROUGE-1）
    test_custom.py              # QualityEvaluator 单元测试
    test_faithfulness.py        # FaithfulnessEvaluator 单元测试
    test_composite.py           # CompositeEvaluator + MetricsReporter 单元测试
    test_e2e.py                 # AgentEvaluator 端到端集成测试
  apps/
    app.py                      # root_agent 定义（供 AgentEvaluator 使用）
    main.py                     # 入口：MODE=manual / MODE=e2e
  reports/                      # MetricsReporter 输出的 JSON 报告
  docs/
    architecture.md             # Mermaid 架构图
```

## 运行方式

```bash
cd phases/07-evaluation/

# 手动评测（不需要 LLM API，演示全部 6 种评估器）
MODE=manual python apps/main.py

# 端到端评测（需要 Gemini API key）
MODE=e2e python apps/main.py

# pytest 运行离线测试（33 个测试）
pytest tests/test_trajectory.py tests/test_response.py tests/test_custom.py \
       tests/test_faithfulness.py tests/test_composite.py -v

# pytest 运行全部（包括需要 API 的端到端测试）
pytest tests/ -v
```
