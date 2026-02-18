# 回调与插件：架构说明

## 核心理念

Agent 不应包含日志、安全、监控等横切逻辑——通过 Callback 和 Plugin 注入。

## 9 种回调的触发时序

```mermaid
sequenceDiagram
    participant User
    participant BA as before_agent
    participant BM as before_model
    participant LLM
    participant AM as after_model
    participant BT as before_tool
    participant Tool
    participant AT as after_tool
    participant AA as after_agent

    User->>BA: 用户请求
    BA->>BM: 继续
    BM->>LLM: 发送 prompt
    LLM-->>AM: LLM 响应（含 tool_call）
    AM->>BT: 需要调工具
    BT->>Tool: 执行工具
    Tool-->>AT: 工具结果
    AT->>BM: 第二轮 LLM
    BM->>LLM: 发送 prompt + 工具结果
    LLM-->>AM: 最终响应
    AM->>AA: Agent 结束
    AA-->>User: 返回结果
```

## 回调返回值效果

```mermaid
flowchart TD
    subgraph "before 回调"
        B1["返回 None"] -->|继续| EXEC["执行（Agent/LLM/Tool）"]
        B2["返回值"] -->|跳过| SKIP["跳过执行，用返回值替代"]
    end

    subgraph "after 回调"
        A1["返回 None"] -->|保持| KEEP["保持原始结果"]
        A2["返回值"] -->|替换| REPLACE["替换原始结果"]
    end

    subgraph "error 回调"
        E1["返回 None"] -->|传播| RAISE["继续抛出异常"]
        E2["返回值"] -->|抑制| SUPPRESS["抑制异常，用返回值替代"]
    end
```

## Plugin vs Callback 执行顺序

```mermaid
sequenceDiagram
    participant P as Plugin
    participant C as Agent Callback
    participant E as 实际执行

    Note over P,E: before_agent 阶段
    P->>P: Plugin.before_agent
    alt Plugin 返回 None
        P->>C: Agent.before_agent_callback
        alt Callback 返回 None
            C->>E: 执行 Agent
        else Callback 返回 Content
            C-->>C: 跳过 Agent
        end
    else Plugin 返回 Content
        P-->>P: 跳过 Agent callback + Agent 执行
    end
```

## Plugin 注册方式

```mermaid
flowchart LR
    subgraph "App（推荐）"
        APP["App(\n  name='my_app',\n  root_agent=agent,\n  plugins=[P1, P2, P3]\n)"]
    end

    subgraph "Plugin 链"
        P1["LoggingPlugin\n（日志）"]
        P2["GuardPlugin\n（安全）"]
        P3["CostTrackerPlugin\n（成本）"]
    end

    APP --> RUNNER["Runner(\n  app=app,\n  session_service=...\n)"]

    P1 --> P2 --> P3

    RUNNER --> AGENT["research_agent\n+ Agent Callbacks"]
```

## Callback 签名一览

```mermaid
classDiagram
    class AgentCallbacks {
        before_agent(CallbackContext) Optional~Content~
        after_agent(CallbackContext) Optional~Content~
    }

    class ModelCallbacks {
        before_model(CallbackContext, LlmRequest) Optional~LlmResponse~
        after_model(CallbackContext, LlmResponse) Optional~LlmResponse~
        on_model_error(CallbackContext, LlmRequest, Exception) Optional~LlmResponse~
    }

    class ToolCallbacks {
        before_tool(BaseTool, dict, ToolContext) Optional~dict~
        after_tool(BaseTool, dict, ToolContext, dict) Optional~dict~
        on_tool_error(BaseTool, dict, ToolContext, Exception) Optional~dict~
    }

    class BasePlugin {
        <<ABC>>
        +before_agent_callback(*, agent, callback_context)
        +after_agent_callback(*, agent, callback_context)
        +before_model_callback(*, callback_context, llm_request)
        +after_model_callback(*, callback_context, llm_response)
        +on_model_error_callback(*, callback_context, llm_request, error)
        +before_tool_callback(*, tool, tool_args, tool_context)
        +after_tool_callback(*, tool, tool_args, tool_context, result)
        +on_tool_error_callback(*, tool, tool_args, tool_context, error)
        +before_run_callback(*, invocation_context)
        +after_run_callback(*, invocation_context)
        +on_event_callback(*, invocation_context, event)
        +close()
    }
```

## GenerateContentConfig 参数

```mermaid
flowchart TD
    subgraph "LlmAgent 配置"
        GCC["GenerateContentConfig"]
        GCC --> T["temperature: 0.3\n（确定性 ↔ 随机性）"]
        GCC --> M["max_output_tokens: 500\n（输出长度上限）"]
        GCC --> P["top_p: 0.9\n（核采样）"]
        GCC --> S["stop_sequences\n（停止序列）"]
    end

    subgraph "不能用 config 设置"
        X1["tools → LlmAgent.tools"]
        X2["system_instruction → LlmAgent.instruction"]
        X3["thinking_config → LlmAgent.planner"]
    end

    style X1 fill:#f66
    style X2 fill:#f66
    style X3 fill:#f66
```

## CallbackContext vs ToolContext

```mermaid
classDiagram
    class ReadonlyContext {
        +user_content: Content
        +invocation_id: str
        +agent_name: str
        +session: Session
        +state: MappingProxyType
    }

    class CallbackContext {
        +state: State（可变）
        +load_artifact()
        +save_artifact()
        +save_credential()
        +load_credential()
    }

    class ToolContext {
        +function_call_id: str
        +actions: EventActions
        +search_memory()
        +request_credential()
        +request_confirmation()
    }

    ReadonlyContext <|-- CallbackContext : 扩展为可变
    CallbackContext <|-- ToolContext : 扩展工具能力

    note for CallbackContext "Agent/Model 回调使用"
    note for ToolContext "Tool 回调使用"
```

## 三个 Plugin 的职责

```mermaid
flowchart TD
    REQ["用户请求"] --> LP["LoggingPlugin\n记录所有事件"]
    REQ --> GP["GuardPlugin\n检查敏感词"]
    REQ --> CT["CostTrackerPlugin\n统计 token"]

    LP --> LOG["控制台日志\n#001 AGENT: starting\n#002 MODEL: sending..."]

    GP -->|安全| PASS["放行"]
    GP -->|敏感词| BLOCK["拦截\n返回安全提示"]

    CT --> SUMMARY["成本摘要\nLLM calls: 2\nTotal tokens: 450"]

    style BLOCK fill:#f66
```

## 完整执行流程

```mermaid
flowchart TD
    A["apps/main.py"] --> B{DEMO}
    B -->|callbacks| C["Agent 级回调演示"]
    B -->|plugins| D["全局插件演示"]

    C --> C1["Runner(\n  agent=root_agent,\n  session_service=...\n)"]
    C1 --> C2["root_agent 自带 9 种回调"]
    C2 --> C3["执行 → 观察回调日志"]

    D --> D1["App(\n  root_agent=bare_agent,\n  plugins=[log, guard, cost]\n)"]
    D1 --> D2["Runner(app=app)"]
    D2 --> D3["执行 → 观察插件日志"]

    C3 --> OUT["控制台输出\n回调触发顺序 + state 变化"]
    D3 --> OUT2["控制台输出\n插件日志 + 成本统计"]
```
