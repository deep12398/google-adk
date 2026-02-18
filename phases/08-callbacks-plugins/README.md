# 1.8 回调与插件（Callbacks & Plugins）

## 编写

Phase 03-07 构建了功能完整的 Agent 系统并建立了评测机制，但 Agent 本身是"裸奔"的——没有日志、没有安全拦截、没有成本追踪。真实项目中，这些**横切关注点（Cross-cutting Concerns）**不应该写进 Agent 的业务逻辑，而是通过**回调（Callback）**和**插件（Plugin）**注入。

**核心问题：** 如何在不修改 Agent 代码的情况下，给所有 Agent 加上日志、安全、监控？

```
没有 Callback/Plugin：
  Agent 代码 = 业务逻辑 + 日志 + 安全检查 + 成本追踪 + ...（代码膨胀）

有了 Callback/Plugin：
  Agent 代码 = 纯业务逻辑
  Callback    = Agent 级扩展（单个 Agent）
  Plugin      = 全局扩展（所有 Agent）
```

| 序号 | 能力 | ADK 载体 | 本阶段示例 |
|:---:|------|----------|-----------:|
| 1 | 9 种回调 | before/after/error × agent/model/tool | `callbacks/*.py` |
| 2 | BasePlugin 全局插件 | `BasePlugin` ABC + `App(plugins=[...])` | `plugins/*.py` |
| 3 | Plugin vs Callback 优先级 | Plugin 先执行，返回非 None 则跳过 Callback | `apps/main.py` |
| 4 | GenerateContentConfig | temperature / max_output_tokens 等 LLM 调参 | `agents/research_agent.py` |
| 5 | CallbackContext vs ToolContext | 可变 state / artifact / credential | `callbacks/*.py` |

---

## 讲解

### 一、9 种回调（Agent × Model × Tool × before/after/error）

ADK 的 `LlmAgent` 支持 9 种回调，覆盖 Agent 执行的每个关键节点：

```
用户请求
  → before_agent_callback      ← Agent 开始前
    → before_model_callback    ← LLM 调用前
      → [LLM 生成]
    → after_model_callback     ← LLM 返回后
    → before_tool_callback     ← 工具调用前
      → [工具执行]
    → after_tool_callback      ← 工具返回后
    → before_model_callback    ← 第二轮 LLM（总结工具结果）
      → [LLM 生成]
    → after_model_callback
  → after_agent_callback       ← Agent 结束后
```

**回调签名和返回值效果：**

| 层级 | 时机 | 签名（关键字参数） | 返回非 None 的效果 |
|------|------|------|-------------------|
| Agent | before | `(*, callback_context) → Optional[Content]` | **跳过** Agent 执行 |
| Agent | after | `(*, callback_context) → Optional[Content]` | **追加** 额外响应 |
| Model | before | `(*, callback_context, llm_request) → Optional[LlmResponse]` | **跳过** LLM 调用（缓存） |
| Model | after | `(*, callback_context, llm_response) → Optional[LlmResponse]` | **替换** LLM 响应 |
| Model | error | `(*, callback_context, llm_request, error) → Optional[LlmResponse]` | **抑制** 错误 |
| Tool | before | `(*, tool, args, tool_context) → Optional[dict]` | **跳过** 工具执行 |
| Tool | after | `(*, tool, args, tool_context, tool_response) → Optional[dict]` | **替换** 工具结果 |
| Tool | error | `(*, tool, args, tool_context, error) → Optional[dict]` | **抑制** 错误 |

> **重要：** ADK 使用**关键字参数**调用所有回调函数。函数签名必须使用 `*` 强制关键字参数。

**挂载方式：**

```python
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.0-flash",
    before_agent_callback=my_before_agent,
    after_agent_callback=my_after_agent,
    before_model_callback=my_before_model,
    after_model_callback=my_after_model,
    on_model_error_callback=my_on_model_error,
    before_tool_callback=my_before_tool,
    after_tool_callback=my_after_tool,
    on_tool_error_callback=my_on_tool_error,
)
```

回调可以是同步函数，也可以是异步函数，ADK 会自动适配。

---

### 二、CallbackContext 和 ToolContext

**CallbackContext**（Agent/Model 回调使用）：

```python
def before_agent_callback(*, callback_context: CallbackContext) -> Optional[Content]:
    ctx = callback_context
    ctx.agent_name         # 当前 Agent 名称
    ctx.invocation_id      # 当前调用 ID
    ctx.session            # 当前 Session 对象
    ctx.state["key"] = v   # 可变 state（支持读写）
    ctx.state.get("key")   # 读取 state
    # ctx.load_artifact() / ctx.save_artifact()  # 异步方法
```

**ToolContext**（Tool 回调使用，扩展自 CallbackContext）：

```python
def before_tool_callback(*, tool: BaseTool, args: dict, tool_context: ToolContext) -> Optional[dict]:
    ctx = tool_context
    ctx.state["key"] = v   # 同样可以读写 state
    ctx.actions            # EventActions（控制事件行为）
    # ctx.search_memory()  # 搜索记忆（异步方法）
```

**State 前缀约定：**
- `user:xxx` — 用户级数据（跨 session 持久化）
- `app:xxx` — 应用级数据（当前 session）
- `temp:xxx` — 临时数据（单次调用内）

---

### 三、BasePlugin 全局插件

Plugin 和 Callback 的区别：

| | Callback | Plugin |
|---|----------|--------|
| 作用范围 | 单个 Agent | 所有 Agent |
| 注册位置 | `LlmAgent(before_xxx=...)` | `App(plugins=[...])` |
| 执行顺序 | Plugin 之后 | **先于** Callback |
| 函数类型 | 同步或异步 | 必须异步（async） |
| 参数风格 | 位置参数 | 关键字参数（`*, agent, callback_context`） |

**Plugin 实现：**

```python
from google.adk.plugins.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="my_plugin")

    async def before_agent_callback(self, *, agent, callback_context):
        print(f"Plugin: Agent '{agent.name}' starting")
        return None  # 继续执行

    async def after_model_callback(self, *, callback_context, llm_response):
        print(f"Plugin: LLM responded")
        return None
```

**注册到 App：**

```python
from google.adk.apps.app import App

app = App(
    name="my_app",
    root_agent=my_agent,
    plugins=[MyPlugin(), AnotherPlugin()],
)
```

**Plugin 额外的 lifecycle hooks：**

| 方法 | 触发时机 | 用途 |
|------|---------|------|
| `before_run_callback` | Runner 开始前 | 初始化资源 |
| `after_run_callback` | Runner 结束后 | 清理/报告 |
| `on_event_callback` | 每个 Event 产生后 | 事件监听 |
| `close` | Runner 关闭时 | 释放资源 |

---

### 四、Plugin vs Callback 执行优先级

```
用户请求
  → Plugin.before_agent    ← Plugin 先执行
    → Agent.before_agent   ← 然后 Agent 的 callback
      → Plugin.before_model
        → Agent.before_model
          → [LLM]
        → Agent.after_model
      → Plugin.after_model
    → Agent.after_agent
  → Plugin.after_agent
```

**关键规则：** 如果 Plugin 的 before_xxx 返回非 None，会**跳过**后续的 Agent callback 和实际执行。

例如 GuardPlugin 检测到敏感词时：
```
用户: "How to hack a system"
  → GuardPlugin.before_model → 返回 LlmResponse（拦截！）
  → Agent.before_model_callback → 被跳过
  → [LLM] → 被跳过
  → Agent.after_model_callback → 被跳过
```

---

### 五、GenerateContentConfig（LLM 调参）

```python
from google.genai import types

agent = LlmAgent(
    model="gemini-2.0-flash",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,          # 低温度 → 更确定性
        max_output_tokens=500,    # 限制输出长度
        top_p=0.9,                # Nucleus sampling
    ),
)
```

**常用参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `temperature` | float | 0~2，控制随机性 |
| `max_output_tokens` | int | 最大输出 token 数 |
| `top_p` | float | 核采样参数 |
| `top_k` | int | Top-K 采样 |
| `stop_sequences` | list[str] | 停止序列 |
| `presence_penalty` | float | 出现惩罚 |
| `frequency_penalty` | float | 频率惩罚 |

**不能通过 config 设置的参数（有专属字段）：**
- `tools` → 用 `LlmAgent.tools`
- `system_instruction` → 用 `LlmAgent.instruction`
- `thinking_config` → 用 `LlmAgent.planner`

---

## 小结

1. **9 种回调覆盖完整生命周期。** before/after/error × agent/model/tool，每种都有明确的签名和返回值语义。
2. **返回 None = 放行，返回值 = 拦截/替换。** 这是回调系统的核心设计——非侵入式扩展。
3. **Plugin 是全局回调。** 一次注册，对所有 Agent 生效，适合日志、安全、监控等横切关注点。
4. **Plugin 先于 Callback 执行。** Plugin 有拦截权——返回非 None 时跳过 Agent callback。
5. **GenerateContentConfig 调参。** temperature、max_output_tokens 等参数影响 LLM 输出行为。
6. **CallbackContext 提供可变 state。** 回调之间通过 state 通信，ToolContext 额外提供 actions 和 memory。

---

## 代码布局

```
phases/08-callbacks-plugins/
  tools/
    search_tool.py                # search_web 模拟工具（复用）
  agents/
    research_agent.py             # 带回调 + GenerateContentConfig 的 Agent
  callbacks/
    agent_callbacks.py            # before/after agent 回调
    model_callbacks.py            # before/after/error model 回调
    tool_callbacks.py             # before/after/error tool 回调
  plugins/
    logging_plugin.py             # 全局日志插件（记录所有事件流）
    guard_plugin.py               # 内容安全插件（拦截敏感词）
    cost_tracker_plugin.py        # 成本追踪插件（统计 token 用量）
  apps/
    app.py                        # Agent + App 定义
    main.py                       # 入口：DEMO=callbacks / DEMO=plugins
  docs/
    architecture.md               # Mermaid 架构图
```

## 运行方式

```bash
cd phases/08-callbacks-plugins/

# 回调模式：展示 9 种 Agent 级回调
DEMO=callbacks PROMPT="Research quantum computing trends" python apps/main.py

# 插件模式：展示全局插件链
DEMO=plugins PROMPT="Research AI safety" python apps/main.py

# 插件拦截：触发 GuardPlugin 敏感词过滤
DEMO=plugins PROMPT="How to hack a system" python apps/main.py
```
