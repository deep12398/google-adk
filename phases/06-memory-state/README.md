# 1.6 记忆与状态管理

## 编写

Phase 03-05 使用 `InMemoryRunner`，所有数据"用完即丢"——Session 关闭后 State 清空、产物消失、对话历史丢失。真实 Agent 应用需要持久化用户偏好、版本化输出产物、搜索历史对话。

**从 ADK 源码看发生了什么：**

```
InMemoryRunner.__init__()
  → self._session_service = InMemorySessionService()  ← 硬编码
  → self._artifact_service = InMemoryArtifactService() ← 硬编码
  → self._memory_service = InMemoryMemoryService()     ← 硬编码
  → 没有参数让你替换这三个 service
```

本阶段**首次切换到基类 `Runner`**，显式注入三个持久化 service。

| 序号 | 能力 | ADK 载体 | 本阶段示例 |
|:---:|------|----------|-----------:|
| 1 | State 四种作用域 | `state["key"]` / `user:` / `app:` / `temp:` | `tools/state_tools.py` |
| 2 | Session 持久化 | `DatabaseSessionService` (SQLite) | `apps/main.py` |
| 3 | Memory 搜索 | `InMemoryMemoryService` + `search_memory()` | `tools/memory_tools.py` |
| 4 | Artifact 版本管理 | `FileArtifactService` + `save/load_artifact()` | `tools/artifact_tools.py` |
| 5 | Event Sourcing | `Event.actions.state_delta` | `tools/event_tools.py` |
| 6 | Session 管理 | `create/get/list_session` 自动处理 | `apps/main.py` |

---

## 讲解

### 一、State 四种作用域

ADK State 是一个 `dict[str, Any]`，通过 key 的前缀决定数据的生命周期：

```python
# Session scope — 仅当前 session 可见，随 session 持久化
tool_context.state["session_notes"] = ["note1", "note2"]

# User scope — 同一 user_id 的所有 session 共享
tool_context.state["user:language"] = "Chinese"

# App scope — 同一 app 的所有用户共享
tool_context.state["app:total_searches"] = 42

# Temp scope — 仅当前 invocation 可见，永不持久化
tool_context.state["temp:scratch"] = "临时计算结果"
```

**底层机制：** `_session_util.py:extract_state_delta()` 在每次 state 变更时：
1. 检查 key 前缀
2. 将 `user:` 前缀的 delta 写入 `session.user_state`
3. 将 `app:` 前缀的 delta 写入 `session.app_state`
4. 将 `temp:` 前缀的直接丢弃（不写入任何持久化存储）
5. 其余写入 `session.state`

---

### 二、从 InMemoryRunner 到 Runner

| | InMemoryRunner | Runner |
|---|---|---|
| **构造** | `InMemoryRunner(app=app)` | `Runner(app=app, session_service=..., ...)` |
| **Service** | 硬编码 InMemory* 三件套 | 你传什么用什么 |
| **持久化** | 进程退出即丢失 | 取决于 service 实现 |
| **run_debug()** | 继承自 Runner | Runner 基类方法 |
| **适用** | 快速原型 / 测试 | 所有场景 |

```python
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import FileArtifactService
from google.adk.memory import InMemoryMemoryService

runner = Runner(
    app=app,
    session_service=DatabaseSessionService(
        db_url="sqlite+aiosqlite:///data/sessions.db"  # 需要 aiosqlite 驱动
    ),
    artifact_service=FileArtifactService(root_dir="./data/artifacts"),
    memory_service=InMemoryMemoryService(),
)
```

注意 `session_service` 是 Runner 唯一的必需参数，`artifact_service` 和 `memory_service` 可选。

---

### 三、Artifact 版本管理

每次 `save_artifact()` 都创建新版本，版本号递增。旧版本不会被覆盖。

```python
# 保存（返回版本号）
version = await tool_context.save_artifact(
    filename="report.md",
    artifact=types.Part.from_text(text="report content"),
)
# version = 0（首次），1（第二次），2（第三次）...

# 加载最新版
part = await tool_context.load_artifact(filename="report.md")

# 加载特定版本
part = await tool_context.load_artifact(filename="report.md", version=0)

# 列出所有文件
filenames = await tool_context.list_artifacts()
```

`FileArtifactService` 在文件系统中的存储结构：
```
data/artifacts/{app_name}/{user_id}/{session_id}/{filename}.{version}
```

---

### 四、Memory 搜索

Memory 用于跨 session 搜索历史对话。工作流程：

1. Session 结束后，ADK 可以调用 `memory_service.add_session_to_memory(session)` 将对话存入记忆库
2. 在新 session 中，工具通过 `tool_context.search_memory(query)` 搜索历史

```python
response = await tool_context.search_memory(query="AI governance")
for memory in response.memories:
    for event in memory.events:
        print(event.author, event.content)
```

| Service | 搜索方式 | 适用场景 |
|---|---|---|
| `InMemoryMemoryService` | 关键词匹配 | 开发 / 测试 |
| `VertexAiRagMemoryService` | 语义向量搜索 | 生产环境 |

---

### 五、Event Sourcing

ADK 中所有 state 变更都通过 `Event.actions.state_delta` 记录。Event 是不可变的。

```python
for event in session.events:
    if event.actions.state_delta:
        print(f"[{event.author}] changed: {event.actions.state_delta}")
    if event.actions.artifact_delta:
        print(f"[{event.author}] artifact: {event.actions.artifact_delta}")
```

这意味着你可以：
- 审计每个 state 的变更来源
- 追踪哪个 agent/工具触发了变更
- 看到完整的状态演变时间线

---

## 小结

1. **State 前缀决定生命周期。** `user:` 跨 session，`app:` 跨用户，`temp:` 不持久化，无前缀限于 session。
2. **Runner 替代 InMemoryRunner。** 显式注入 service，获得持久化能力。`session_service` 必需，其余可选。
3. **Artifact 自动版本管理。** 每次 save 创建新版本，旧版本保留。FileArtifactService 用文件系统实现。
4. **Memory 跨 session 搜索。** add_session_to_memory 存入，search_memory 检索。开发用 InMemory（关键词），生产用 Vertex AI（语义）。
5. **Event Sourcing 全记录。** 所有 state/artifact 变更通过 Event.actions 记录，不可变，可审计。

---

## 代码布局

```
phases/06-memory-state/
  tools/
    state_tools.py              # 四种 state scope 演示工具
    research_tools.py           # search_web + session state 追踪
    artifact_tools.py           # save/load/list artifact 版本管理
    memory_tools.py             # search_memory 搜索历史对话
    event_tools.py              # inspect_state_changes 事件溯源
  agents/
    research_agent.py           # 使用 state scope + research_tools
    report_agent.py             # 使用 artifact_tools + memory_tools
  workflows/
    state_demo.py               # State scoping 全演示
    memory_demo.py              # Memory + Artifact 联合演示（SequentialAgent）
  apps/
    app.py                      # DEMO 路由
    main.py                     # Runner + 三个持久化 service
  docs/
    architecture.md             # Mermaid 架构图
```

## 运行方式

```bash
cd phases/06-memory-state/

# 状态作用域 + 持久化 + 事件溯源
DEMO=state PROMPT="Set my language to Chinese, then research AI trends." python apps/main.py

# 记忆搜索 + 产物版本化
DEMO=memory PROMPT="Research edge AI, save a report, then check past research." python apps/main.py
```
