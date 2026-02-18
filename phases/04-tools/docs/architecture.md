# 工具调用与工程化组织：架构说明

本阶段展示 ADK 工具系统的六大能力：FunctionTool、ToolContext、Callbacks、Confirmation、AgentTool、LongRunningFunctionTool。

## 组件与职责

- `tools/`：工具定义层，每个文件一类工具能力
- `callbacks/`：跨切面层，可观测性与安全回调
- `agents/`：认知层，使用工具的 Agent 角色
- `workflows/`：编排层，组合 Agent 的流水线
- `apps/`：入口层，DEMO 路由 + Runner

## 总体流程图

```mermaid
flowchart TD
  A[apps/main.py] --> B[apps/app.py: choose root_agent]
  B --> C{DEMO}
  C -->|basics| D[research_agent]
  C -->|agent_tool| E[coordinator_agent]
  C -->|pipeline| F[SequentialAgent]
  D --> G[tools/search_tool.py]
  E --> G
  E --> H[tools/agent_as_tool.py]
  E --> I[tools/confirm_tool.py]
  F --> D
  F --> J[writer_agent]
  J --> K[tools/file_tool.py]
  G -.-> L[callbacks/tool_callbacks.py]
```

## 工具生命周期

```mermaid
flowchart TD
  LLM[LLM 决定调用工具] --> BTC{before_tool_callback}
  BTC -->|返回 dict| SHORT[短路：用 dict 作为结果]
  BTC -->|返回 None| EXEC[执行工具函数]
  EXEC -->|成功| ATC{after_tool_callback}
  EXEC -->|异常| OTE{on_tool_error_callback}
  ATC -->|返回 dict| REPLACE[用返回的 dict 替换结果]
  ATC -->|返回 None| ORIGINAL[使用原始结果]
  OTE -->|返回 dict| FALLBACK[用 dict 作为兜底结果]
  OTE -->|返回 None| RERAISE[重新抛出异常]
  SHORT --> LLM2[LLM 处理结果]
  REPLACE --> LLM2
  ORIGINAL --> LLM2
  FALLBACK --> LLM2
```

## ToolContext 关系图

```mermaid
flowchart LR
  TC[ToolContext] --> S[session.state]
  TC --> A[save_artifact / load_artifact]
  TC --> ACT[actions: escalate, skip_summarization]
  TC --> RC[request_confirmation]
  S --> STATE[(Session State Dict)]
  A --> ART[(Artifact Service)]
```

## AgentTool vs sub_agents

```mermaid
flowchart TD
  subgraph "AgentTool（工具调用）"
    P1[Parent Agent] -->|tool_call| AT[AgentTool: reviewer]
    AT -->|result| P1
    P1 -.->|始终保持控制权| P1
  end
  subgraph "sub_agents（控制权转移）"
    P2[Parent Agent] -->|transfer| SA[Sub Agent: reviewer]
    SA -->|escalate| P2
    P2 -.->|执行期间失去控制权| SA
  end
```

## Pipeline 流程图

```mermaid
flowchart TD
  U[User] --> RA[research_agent]
  RA -->|调用| ST[search_web]
  ST -->|before_callback| LOG1[log + validate]
  ST -->|after_callback| LOG2[audit result]
  ST -->|on_error| ERR[graceful fallback]
  RA --> WA[writer_agent]
  WA -->|调用| FT[save_report_draft]
  FT -->|ToolContext| ART[save artifact]
  WA --> U
```

## Confirmation 流程

```mermaid
sequenceDiagram
  participant LLM
  participant ADK
  participant Tool
  participant User

  LLM->>ADK: call publish_report(file, "public")
  ADK->>ADK: require_confirmation=True → 暂停
  ADK->>User: 请求确认：是否发布到 public？
  User->>ADK: 确认 / 拒绝
  alt 确认
    ADK->>Tool: 执行 publish_report
    Tool->>ADK: {"status": "published"}
    ADK->>LLM: 返回结果
  else 拒绝
    ADK->>LLM: {"error": "Tool call is rejected"}
  end
```
