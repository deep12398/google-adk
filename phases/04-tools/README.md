# 1.4 工具调用与工程化组织（重点）

## 编写

Phase 03 展示了"裸工具"——纯函数挂到 Agent 上就能用。但在工程实践中，工具还需要：
- **参数校验**——防止 LLM 传入非法参数
- **可观测性**——每次工具调用都有日志和审计
- **安全管控**——危险操作需要人工确认
- **错误处理**——外部 API 不可靠时优雅降级
- **能力组合**——把 Agent 本身包装成工具复用

本阶段覆盖 ADK 工具系统的六大能力：

| 序号 | 能力 | ADK 载体 | 本阶段示例文件 |
|:---:|------|----------|-------------|
| 1 | 函数工具与 Schema 自动生成 | `FunctionTool` | `tools/search_tool.py` |
| 2 | 工具上下文（状态 + 产物 + 控制流） | `ToolContext` | `tools/file_tool.py` |
| 3 | 可观测性与安全回调 | `before/after/error_callback` | `callbacks/tool_callbacks.py` |
| 4 | 用户确认门控 | `require_confirmation` | `tools/confirm_tool.py` |
| 5 | Agent 作为工具 | `AgentTool` | `tools/agent_as_tool.py` |
| 6 | 长时间运行工具 | `LongRunningFunctionTool` | `tools/long_running_tool.py` |

---

## 讲解

### 一、FunctionTool——从函数签名到工具 Schema

ADK 最基础的工具形态：**写一个带类型标注的 Python 函数，ADK 自动生成 LLM 可理解的 JSON Schema。**

```python
def search_web(
    query: str,
    max_results: int = 3,
    language: str = "en",
    tool_context: Optional[ToolContext] = None,  # ADK 自动注入，不出现在 schema 中
) -> dict:
    """Search the web for information on a given query.

    Args:
        query: The search query string. Must be non-empty.
        max_results: Maximum number of results to return (1-10).
        language: Language code for results (e.g. 'en', 'zh').
    """
```

**ADK 做了什么：**

| 你写的 | ADK 自动生成的 |
|--------|-------------|
| 函数名 `search_web` | tool name: `"search_web"` |
| docstring 第一行 | tool description |
| `query: str` | `{"type": "string", "description": "The search query..."}` |
| `max_results: int = 3` | `{"type": "integer", "default": 3}` |
| `tool_context: ToolContext` | **跳过**——不出现在 schema 中，由 ADK 运行时注入 |

**类型映射规则：**

| Python 类型 | JSON Schema 类型 |
|------------|-----------------|
| `str` | `STRING` |
| `int` | `INTEGER` |
| `float` | `NUMBER` |
| `bool` | `BOOLEAN` |
| `list` | `ARRAY` |
| `dict` | `OBJECT` |
| Pydantic `BaseModel` | 完整的嵌套 `OBJECT` schema |
| `Optional[T]` | 对应类型，非必填 |

**参数校验——两种策略：**

```python
# 策略 1: 返回错误字典（温和，LLM 会重试）
if not query.strip():
    return {"error": "Query must be non-empty."}

# 策略 2: 抛异常（硬错误，触发 on_tool_error_callback）
if random.random() < 0.15:
    raise ConnectionError("search API temporarily unavailable.")
```

策略 1 适合"参数不对"（LLM 可以纠正后重试），策略 2 适合"服务不可用"（需要上层处理）。

---

### 二、ToolContext——工具与运行时之间的桥梁

`ToolContext` 是 ADK 注入到工具函数中的上下文对象。你通过它访问整个运行时：

```
ToolContext
├── .state                   # 读写 session.state（共享状态字典）
├── .save_artifact()         # 保存版本化产物
├── .load_artifact()         # 读取产物
├── .actions
│   ├── .escalate            # 控制权上升（退出循环等）
│   ├── .skip_summarization  # 跳过 LLM 对工具结果的摘要
│   └── .state_delta         # 状态变更增量
├── .request_confirmation()  # 请求用户确认
└── .search_memory()         # 搜索对话记忆
```

**示例：`save_report_draft` 工具**

```python
async def save_report_draft(
    content: str,
    filename: str = "report_draft.md",
    tool_context: ToolContext = None,
) -> dict:
    # 1. 保存产物（版本化）
    artifact = types.Part.from_text(text=content)
    version = await tool_context.save_artifact(filename=filename, artifact=artifact)

    # 2. 在 state 中记录元数据
    tool_context.state["last_saved_file"] = filename
    tool_context.state["last_saved_version"] = version

    # 3. 跳过 LLM 摘要（直接把工具返回值当最终结果）
    tool_context.actions.skip_summarization = True

    return {"status": "saved", "filename": filename, "version": version}
```

**`skip_summarization` 是什么？**

默认情况下，工具返回结果后，LLM 会"再看一遍"结果并生成一段自然语言摘要。设置 `skip_summarization = True` 可以跳过这一步——适合工具返回值本身就是最终结果、不需要 LLM 再加工的场景（如文件保存确认、状态更新确认）。

**`save_artifact` vs 直接写 state：**

| | `save_artifact` | `state["key"] = value` |
|---|---|---|
| 用途 | 保存文件/大文本 | 保存小型结构化数据 |
| 版本化 | 有（自动递增版本号） | 无（覆盖） |
| 持久化 | 依赖 ArtifactService 实现 | 依赖 SessionService 实现 |
| 适合 | 报告、代码、图片 | 标记、计数器、中间变量 |

---

### 三、Callbacks——可观测性与安全的三道关卡

ADK 在工具执行的生命周期中提供三个回调钩子，**设置在 Agent 上，而非工具上**：

```python
research_agent = LlmAgent(
    tools=[search_web],
    before_tool_callback=log_and_validate_before,   # 执行前
    after_tool_callback=audit_after,                 # 执行后
    on_tool_error_callback=handle_tool_error,        # 异常时
)
```

**为什么设在 Agent 上而不是 Tool 上？** 因为同一个工具可以被多个 Agent 使用，不同 Agent 可能需要不同的安全策略。比如 `search_web` 在研究 Agent 上可以放行一切，但在面向用户的 Agent 上需要过滤敏感词。

#### 三个回调的对比

| | `before_tool_callback` | `after_tool_callback` | `on_tool_error_callback` |
|---|---|---|---|
| **调用时机** | 工具执行**前** | 工具执行**后**（成功时） | 工具**抛异常**时 |
| **参数** | `(tool, args, tool_context)` | `(tool, args, tool_context, result)` | `(tool, args, tool_context, error)` |
| **返回 None** | 继续执行工具 | 使用原始结果 | 重新抛出异常 |
| **返回 dict** | **短路**——跳过执行，用 dict 作为结果 | **替换**——用返回的 dict 替代结果 | **兜底**——用 dict 作为降级结果 |
| **典型用途** | 日志、参数校验、权限检查、屏蔽敏感词 | 审计、结果脱敏、添加元数据 | 优雅降级、错误计数、备用方案 |

#### `before_tool_callback` 示例

```python
def log_and_validate_before(tool, args, tool_context) -> Optional[dict]:
    logger.info(f"[BEFORE] Tool={tool.name}, Args={args}")

    # 拦截敏感词
    query = args.get("query", "")
    for term in ["hack", "exploit"]:
        if term in query.lower():
            return {"error": f"Blocked term: '{term}'"}  # 短路！

    # 计数
    key = f"tool_call_count:{tool.name}"
    tool_context.state[key] = tool_context.state.get(key, 0) + 1

    return None  # 放行
```

#### `on_tool_error_callback` 示例

```python
def handle_tool_error(tool, args, tool_context, error) -> Optional[dict]:
    logger.error(f"[ERROR] Tool={tool.name}, Error={error}")

    # 不崩溃，返回降级结果
    return {
        "error": str(error),
        "fallback": True,
        "suggestion": "Service temporarily unavailable.",
    }
```

**执行顺序图：**

```
LLM 决定调用工具
    │
    ▼
before_tool_callback(tool, args, tool_context)
    │
    ├── 返回 dict → 短路，跳到 LLM 处理结果
    │
    └── 返回 None → 继续
            │
            ▼
        执行工具函数
            │
            ├── 成功 → after_tool_callback(tool, args, tool_context, result)
            │              │
            │              ├── 返回 dict → 替换结果
            │              └── 返回 None → 使用原始结果
            │
            └── 异常 → on_tool_error_callback(tool, args, tool_context, error)
                           │
                           ├── 返回 dict → 降级结果
                           └── 返回 None → 重新抛出
    │
    ▼
LLM 处理结果（除非 skip_summarization=True）
```

---

### 四、Tool Confirmation——危险操作的安全阀

对于破坏性操作（发布、删除、修改），ADK 支持在执行前暂停并等待用户确认。

**三种方式：**

```python
# 方式 1: 静态——所有调用都需要确认
publish_tool = FunctionTool(publish_report, require_confirmation=True)

# 方式 2: 条件——只有特定参数时需要确认
def _needs_confirmation(**kwargs) -> bool:
    return kwargs.get("destination") == "public"

publish_tool = FunctionTool(publish_report, require_confirmation=_needs_confirmation)

# 方式 3: 手动——在工具函数内部控制（高级）
def my_tool(data: str, tool_context: ToolContext) -> dict:
    if not tool_context.tool_confirmation:
        tool_context.request_confirmation(hint="确认执行此操作？")
        return {"status": "awaiting_confirmation"}
    if not tool_context.tool_confirmation.confirmed:
        return {"error": "User rejected the operation."}
    # ... 执行
```

**确认流程：**

```
LLM 调用 publish_report("file.md", "public")
    → ADK 检查 require_confirmation → True
    → 暂停执行，向用户发送确认请求
    → 用户确认 → 执行工具 → 返回结果
    → 用户拒绝 → 返回 {"error": "Tool call is rejected"}
```

**什么时候用哪种：**

| 方式 | 适用场景 |
|------|---------|
| 静态 `True` | 删除、发布、支付——永远需要确认 |
| 条件函数 | 只有特定参数组合才危险（如 destination="public"） |
| 手动 `request_confirmation` | 需要自定义确认消息或复杂判断逻辑 |

---

### 五、AgentTool——把 Agent 当工具用

`AgentTool` 把一个完整的 Agent 包装成工具，让另一个 Agent 可以"调用"它。

```python
from google.adk.tools import AgentTool

review_tool = AgentTool(agent=reviewer_agent)

coordinator = LlmAgent(
    tools=[search_web, review_tool, publish_tool],  # reviewer 作为工具之一
    ...
)
```

**AgentTool vs sub_agents——核心区别：**

| | AgentTool | sub_agents |
|---|---|---|
| **调用方式** | 当作普通工具调用（function call） | 控制权转移（transfer_to_agent） |
| **控制权** | 父 Agent **始终保持**控制权 | 父 Agent **交出**控制权 |
| **执行模型** | 隔离调用：独立的 invocation context | 共享调用：同一个 invocation context |
| **结果处理** | 工具返回结果，父 Agent 继续推理 | 子 Agent 完成后控制权回到父 Agent |
| **适用场景** | "我需要这个 Agent 的意见，但我来决策" | "这个任务交给你了" |

**什么时候用哪个：**

- `AgentTool`：你想在当前 Agent 的推理链中"插入"另一个 Agent 的能力，比如让 coordinator 在写报告的过程中"问一下" reviewer 的意见
- `sub_agents`：你想把整个对话回合交给另一个 Agent 处理，比如用户说"你好"时把控制权交给 greeting_agent

---

### 六、LongRunningFunctionTool——异步长任务

普通工具是同步的——LLM 等工具返回后才继续。`LongRunningFunctionTool` 适合耗时操作：

```python
from google.adk.tools import LongRunningFunctionTool

async def generate_pdf_report(content: str, format: str = "pdf", ...) -> dict:
    await asyncio.sleep(2)  # 模拟耗时操作
    return {"status": "completed", "format": format, "pages": 5}

pdf_report_tool = LongRunningFunctionTool(generate_pdf_report)
```

**执行流程：**

```
LLM 调用 generate_pdf_report(...)
    → ADK 启动异步执行
    → 先返回 pending 状态给 LLM
    → 异步任务完成后，结果通过 function_call_id 匹配并返回
    → LLM 处理最终结果
```

**适用场景：** 外部 API 调用、文件生成、数据处理——任何需要秒级以上等待的操作。

---

### 七、工程化组织——工具、回调、Agent 的分层原则

本阶段引入了一个新目录 `callbacks/`，整体分层如下：

```
tools/          纯工具逻辑（做什么）
callbacks/      跨切面关注点（怎么管控）—— 日志、安全、错误处理
agents/         认知角色（谁来用）—— 决定使用哪些工具和回调
workflows/      编排容器（怎么组合）
apps/           入口路由（怎么启动）
```

**为什么把 callbacks 独立出来？**

- 回调是跨切面关注点（logging、security、error handling），不属于任何单一工具
- 同一个回调可以被多个 Agent 复用
- 修改安全策略不需要动工具代码

**工具组织的设计原则：**

1. **一个文件一类能力**：`search_tool.py` 只做搜索，`file_tool.py` 只做文件操作
2. **工具无状态**：工具函数本身不持有状态，通过 `ToolContext` 读写
3. **回调与工具解耦**：回调设在 Agent 上，不在工具上——同一个工具在不同 Agent 中可以有不同的管控策略
4. **错误处理分三层**：工具内部（预期错误返回 dict）→ 异常（意外错误抛出）→ 回调兜底（跨切面降级）

---

## 小结

1. **FunctionTool 是 ADK 的工具基石。** 类型标注生成 schema，docstring 生成描述，`ToolContext` 连接运行时。
2. **ToolContext 是工具与运行时之间的桥梁。** 状态、产物、控制流都通过它传递。
3. **Callbacks 是可观测性与安全的核心。** before 拦截/校验，after 审计/变换，on_error 兜底——设在 Agent 上而非 Tool 上。
4. **Confirmation 是破坏性操作的安全阀。** 静态、条件、手动三种方式按需选择。
5. **AgentTool 和 sub_agents 是两种组合方式。** 工具调用 = 隔离执行 + 保持控制权；sub_agents = 控制权转移。
6. **错误处理分三层。** 工具内返回错误字典 → 抛异常 → 回调兜底，逐层升级。

---

## 流程图

详见：`phases/04-tools/docs/architecture.md`（包含 Mermaid 格式的工具生命周期、ToolContext 关系、AgentTool vs sub_agents 对比图）

## 代码布局

```
phases/04-tools/
  agents/                              # 认知层：使用工具的 Agent
    research_agent.py                  #   搜索工具 + 三种回调
    writer_agent.py                    #   产物保存工具
    reviewer_agent.py                  #   独立评审 Agent（被 AgentTool 包装）
    coordinator_agent.py               #   协调者：AgentTool + Confirmation + 搜索
  tools/                               # 行动层：工具定义
    search_tool.py                     #   FunctionTool 基础 + ToolContext + 错误注入
    file_tool.py                       #   ToolContext 产物保存 + skip_summarization
    confirm_tool.py                    #   Confirmation 静态 / 条件两种方式
    agent_as_tool.py                   #   AgentTool 包装
    long_running_tool.py               #   LongRunningFunctionTool 异步长任务
  callbacks/                           #  跨切面层：可观测性与安全
    tool_callbacks.py                  #   before / after / on_error 三种回调
  workflows/                           # 编排层
    tool_demo_pipeline.py              #   研究 → 写作 完整流水线
  apps/                                # 入口层
    app.py                             #   DEMO 路由 + App 创建
    main.py                            #   InMemoryRunner + 执行
  docs/
    architecture.md                    #   架构图与生命周期流程图
```

## 运行方式

在 `phases/04-tools/` 目录下：

```bash
# 基础模式：FunctionTool + ToolContext + Callbacks
DEMO=basics PROMPT="Research the current state of WebAssembly." python apps/main.py

# AgentTool + Confirmation 模式
DEMO=agent_tool PROMPT="Research, review, and publish a report on edge AI." python apps/main.py

# 完整流水线：研究（带回调）→ 写作（带产物保存）
DEMO=pipeline PROMPT="Write a comprehensive report on quantum computing." python apps/main.py
```

可用的 `DEMO`：`basics` | `agent_tool` | `pipeline`
