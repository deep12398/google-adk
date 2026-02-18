# 评估与回归：架构说明

## 核心理念

Agent 不是写完就结束——需要可重复的评测机制，在每次修改后验证行为没有退化。

## 评测数据结构

```mermaid
classDiagram
    class EvalSet {
        eval_set_id: str
        eval_cases: list~EvalCase~
    }
    class EvalCase {
        eval_id: str
        conversation: list~Invocation~
        session_input: SessionInput
    }
    class Invocation {
        user_content: Content
        final_response: Content
        intermediate_data: IntermediateData
    }
    class IntermediateData {
        tool_uses: list~FunctionCall~
        tool_responses: list~FunctionResponse~
    }

    EvalSet "1" --> "*" EvalCase
    EvalCase "1" --> "*" Invocation
    Invocation "1" --> "0..1" IntermediateData
```

## TrajectoryEvaluator 三种匹配模式

```mermaid
flowchart LR
    subgraph EXACT
        E_EXP["expected: [A, B]"]
        E_ACT1["actual: [A, B] ✓"]
        E_ACT2["actual: [A, C, B] ✗"]
        E_ACT3["actual: [B, A] ✗"]
    end

    subgraph IN_ORDER
        I_EXP["expected: [A, B]"]
        I_ACT1["actual: [A, B] ✓"]
        I_ACT2["actual: [A, C, B] ✓"]
        I_ACT3["actual: [B, A] ✗"]
    end

    subgraph ANY_ORDER
        A_EXP["expected: [A, B]"]
        A_ACT1["actual: [A, B] ✓"]
        A_ACT2["actual: [A, C, B] ✓"]
        A_ACT3["actual: [B, A] ✓"]
    end
```

## Evaluator 继承体系

```mermaid
classDiagram
    class Evaluator {
        <<ABC>>
        +evaluate_invocations(actual, expected) EvaluationResult
    }
    class TrajectoryEvaluator {
        -threshold: float
        -match_type: MatchType
    }
    class ResponseEvaluator {
        -threshold: float
        -metric_name: str
    }
    class QualityEvaluator {
        -required_tool: str
        -min_response_length: int
    }
    class FaithfulnessEvaluator {
        -faithfulness_weight: float
        -relevancy_weight: float
    }
    class CompositeEvaluator {
        -evaluators: dict
        -threshold: float
        +print_report()
    }

    Evaluator <|-- TrajectoryEvaluator
    Evaluator <|-- ResponseEvaluator
    Evaluator <|-- QualityEvaluator
    Evaluator <|-- FaithfulnessEvaluator
    Evaluator <|-- CompositeEvaluator
    CompositeEvaluator o-- Evaluator : 组合多个

    Note for QualityEvaluator "自定义：工具调用+响应长度"
    Note for FaithfulnessEvaluator "自定义：忠实度+相关度"
    Note for CompositeEvaluator "加权组合任意评估器"
```

## FaithfulnessEvaluator 评分逻辑

```mermaid
flowchart TD
    INV[Invocation] --> TR["提取 tool_responses<br/>（工具返回内容）"]
    INV --> FR["提取 final_response<br/>（Agent 回答）"]
    INV --> UC["提取 user_content<br/>（用户问题）"]

    TR --> TK["关键词集合 A"]
    FR --> RK["关键词集合 B"]
    UC --> QK["关键词集合 C"]

    TK --> FAITH["faithfulness<br/>= |A ∩ B| / |B|<br/>回答在工具输出中的覆盖率"]
    RK --> FAITH
    RK --> RELEV["relevancy<br/>= |B ∩ C| / |C|<br/>回答与问题的重叠率"]
    QK --> RELEV

    FAITH -->|× 0.6| SCORE["score = faith × 0.6 + relev × 0.4"]
    RELEV -->|× 0.4| SCORE
```

## CompositeEvaluator 加权组合

```mermaid
flowchart LR
    subgraph 子评估器
        T["TrajectoryEvaluator<br/>score=1.0"]
        F["FaithfulnessEvaluator<br/>score=0.0"]
        Q["QualityEvaluator<br/>score=1.0"]
    end

    T -->|"× 30%"| W1["0.300"]
    F -->|"× 40%"| W2["0.000"]
    Q -->|"× 30%"| W3["0.300"]

    W1 --> SUM["综合分 = 0.600"]
    W2 --> SUM
    W3 --> SUM

    SUM -->|">= 0.5"| PASS["PASSED ✓"]
    SUM -->|"< 0.5"| FAIL["FAILED ✗"]

    style F fill:#f66
    style W2 fill:#f66
```

## 幻觉检测示例

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Tool as search_web
    participant FE as FaithfulnessEvaluator

    User->>Agent: Research AI trends
    Agent->>Tool: search_web("AI trends")
    Tool-->>Agent: "AI trends: automation, scalability..."
    Agent-->>User: "The weather is sunny today..." ← 幻觉！

    Note over FE: 检查回答 vs 工具输出
    FE->>FE: 回答关键词: weather, sunny, today...
    FE->>FE: 工具关键词: AI, automation, scalability...
    FE->>FE: 交集 = {} → faithfulness = 0.0
    FE-->>User: FAILED（Agent 在瞎编）
```

## MetricsReporter 报告流程

```mermaid
flowchart TD
    E1["评测用例 1"] --> R["MetricsReporter"]
    E2["评测用例 2"] --> R
    E3["评测用例 3"] --> R

    R --> AGG["汇总统计<br/>avg / min / max<br/>pass_rate"]
    R --> DET["详细结果<br/>每个用例的各维度分数"]

    AGG --> JSON["eval_report_20260216.json"]
    DET --> JSON

    JSON --> HIST["历史对比<br/>检测回归"]
```

## 评测执行流程

```mermaid
sequenceDiagram
    participant F as .test.json
    participant AE as AgentEvaluator
    participant Agent as research_agent
    participant TE as TrajectoryEvaluator
    participant RE as ResponseEvaluator
    participant R as EvaluationResult

    F->>AE: 加载 EvalSet
    Note over AE: 读取 test_config.json

    loop 每个 EvalCase
        AE->>Agent: 运行 Agent（user_content）
        Agent-->>AE: actual Invocations

        AE->>TE: evaluate_invocations(actual, expected)
        TE-->>AE: trajectory score

        AE->>RE: evaluate_invocations(actual, expected)
        RE-->>AE: response score
    end

    AE->>R: 汇总所有指标
    R-->>AE: PASSED / FAILED
```

## 总体流程图

```mermaid
flowchart TD
    A["apps/main.py"] --> B{MODE}
    B -->|manual| C["手动构造 Invocation"]
    B -->|e2e| D["AgentEvaluator.evaluate()"]

    C --> E["TrajectoryEvaluator<br/>（三种 MatchType）"]
    C --> F["ResponseEvaluator<br/>（ROUGE-1）"]
    C --> G["QualityEvaluator<br/>（工具调用+长度）"]
    C --> H["FaithfulnessEvaluator<br/>（忠实度+相关度）"]
    C --> I["CompositeEvaluator<br/>（加权组合）"]

    I --> J["MetricsReporter<br/>（JSON 报告）"]

    D --> K["加载 .test.json"]
    K --> L["运行 Agent"]
    L --> M["评估 + Assert"]

    E --> N["EvaluationResult"]
    F --> N
    G --> N
    H --> N
    I --> N

    J --> O["reports/eval_report_*.json"]

    subgraph "eval_data/"
        K1["research.test.json"]
        K2["multi_turn.test.json"]
        K3["test_config.json"]
    end
    K --> K1
    K --> K2
    K --> K3
```

## n6-agent 对比

```mermaid
flowchart LR
    subgraph "n6-agent（生产级）"
        N1["RAGAS 12 指标"]
        N2["LangSmith Tracing"]
        N3["OpenTelemetry + Prometheus"]
        N4["overall_rag_score<br/>= retrieval × 0.4 + generation × 0.6"]
        N5["JSON 评测报告<br/>langsmith_metrics_evaluation_report.json"]
    end

    subgraph "Phase 07（教学版）"
        P1["6 种 Evaluator"]
        P2["ADK 内置 Tracing"]
        P3["—"]
        P4["CompositeEvaluator<br/>= trajectory × 0.3 + faith × 0.4 + quality × 0.3"]
        P5["MetricsReporter<br/>eval_report_*.json"]
    end

    N1 -.->|"简化"| P1
    N4 -.->|"同理念"| P4
    N5 -.->|"同格式"| P5
```
