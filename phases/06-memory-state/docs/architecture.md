# 记忆与状态管理：架构说明

## 核心理念

从 InMemoryRunner（一切用完即丢）切换到 Runner + 持久化 Service（数据长期保存）。

## InMemoryRunner vs Runner

```mermaid
flowchart LR
  subgraph "Phase 03-05: InMemoryRunner"
    IR["InMemoryRunner(app)"] --> IS[InMemorySessionService]
    IR --> IA[InMemoryArtifactService]
    IR --> IM[InMemoryMemoryService]
    IS -.->|进程退出| GONE["❌ 数据丢失"]
    IA -.->|进程退出| GONE
  end
  subgraph "Phase 06: Runner + 持久化"
    R["Runner(app, services...)"] --> DS[DatabaseSessionService]
    R --> FA[FileArtifactService]
    R --> MM[InMemoryMemoryService]
    DS -->|SQLite| DB[(sessions.db)]
    FA -->|文件系统| FS[("artifacts/")]
  end
```

## State 四种作用域

```mermaid
flowchart TD
  STATE["tool_context.state"] --> S1["无前缀 → session scope"]
  STATE --> S2["user: → user scope"]
  STATE --> S3["app: → app scope"]
  STATE --> S4["temp: → temp scope"]

  S1 -->|持久化到| SS["session_state<br/>仅当前 session 可见"]
  S2 -->|持久化到| US["user_state<br/>同一 user 的所有 session 共享"]
  S3 -->|持久化到| AS["app_state<br/>所有用户共享"]
  S4 -->|不持久化| NONE["丢弃<br/>仅当前 invocation 可见"]
```

## State Scope 生命周期

```mermaid
sequenceDiagram
  participant User
  participant Session1 as Session A
  participant Session2 as Session B
  participant DB as 持久化存储

  User->>Session1: state["user:lang"] = "zh"
  Session1->>DB: 写入 user_state
  User->>Session1: state["session_notes"] = [...]
  Session1->>DB: 写入 session_state
  User->>Session1: state["temp:scratch"] = "tmp"
  Note over Session1: temp 不写入 DB

  Note over User: 新建 Session B
  User->>Session2: 读 state["user:lang"]
  DB->>Session2: "zh" ✓（user scope 共享）
  User->>Session2: 读 state["session_notes"]
  Note over Session2: None（session scope 不共享）
```

## Artifact 版本管理

```mermaid
sequenceDiagram
  participant Agent
  participant TC as ToolContext
  participant FAS as FileArtifactService
  participant FS as 文件系统

  Agent->>TC: save_artifact("report.md", content_v1)
  TC->>FAS: save(filename, part)
  FAS->>FS: 写入 report.md.0
  FAS-->>TC: version=0

  Agent->>TC: save_artifact("report.md", content_v2)
  TC->>FAS: save(filename, part)
  FAS->>FS: 写入 report.md.1
  FAS-->>TC: version=1

  Agent->>TC: load_artifact("report.md")
  TC->>FAS: load(filename, version=None)
  FAS->>FS: 读取 report.md.1（最新）
  FAS-->>TC: content_v2

  Agent->>TC: load_artifact("report.md", version=0)
  TC->>FAS: load(filename, version=0)
  FAS->>FS: 读取 report.md.0
  FAS-->>TC: content_v1
```

## Event Sourcing

```mermaid
flowchart LR
  E1["Event #1<br/>author: user<br/>state_delta: {}"] --> E2["Event #2<br/>author: research_agent<br/>state_delta: {user:lang → zh}"]
  E2 --> E3["Event #3<br/>author: research_agent<br/>state_delta: {app:total_searches → 1}"]
  E3 --> E4["Event #4<br/>author: report_agent<br/>artifact_delta: {report.md → 0}"]

  E1 -.-> |不可变| E1
  E2 -.-> |不可变| E2
  E3 -.-> |不可变| E3
  E4 -.-> |不可变| E4
```

## Memory 搜索流程

```mermaid
sequenceDiagram
  participant S1 as Session 1（已结束）
  participant MEM as MemoryService
  participant S2 as Session 2（当前）
  participant Agent

  Note over S1: 包含 AI governance 研究对话
  S1->>MEM: add_session_to_memory(session1)

  Agent->>S2: search_memory("AI governance")
  S2->>MEM: search(query, app_name, user_id)
  MEM-->>S2: SearchMemoryResponse(memories=[...])
  S2-->>Agent: 历史对话片段
```

## 总体流程图

```mermaid
flowchart TD
  A[apps/main.py] --> B[Runner + 3 Services]
  B --> C[apps/app.py: choose root_agent]
  C --> D{DEMO}
  D -->|state| E["research_agent<br/>(state_tools + research_tools + event_tools)"]
  D -->|memory| F["SequentialAgent"]
  F --> G["research_agent<br/>(研究 → state)"]
  F --> H["report_agent<br/>(memory_tools + artifact_tools)"]

  B --> SS[(DatabaseSessionService<br/>SQLite)]
  B --> AS[(FileArtifactService<br/>文件系统)]
  B --> MS[InMemoryMemoryService]
```
