# 1.3 多智能体编排（重点）

## 编写

多智能体编排的核心是"任务分解 + 责任边界"。
本阶段展示两类编排方式：
1) **委派式（Delegation）**：由一个根 Agent（LlmAgent）基于 `description` 与 `instruction` 把任务委派给子 Agent。
2) **工作流式（Workflow）**：用确定性流程（串行/并行/循环）编排多 Agent，不依赖 LLM 做路由决策。

这两类方式不是"二选一"，而是可以**嵌套组合**的。比如一个 `SequentialAgent` 的某一步可以是一个带 `sub_agents` 的 LlmAgent（委派式），反过来也一样。

---

## 讲解

### 一、两类编排的本质区别

| 维度 | 委派式 (Delegation) | 工作流式 (Workflow) |
|------|-------------------|-------------------|
| **路由决策者** | LLM 根据上下文自主判断 | 代码结构（确定性） |
| **ADK 载体** | `LlmAgent` + `sub_agents` 参数 | `SequentialAgent` / `ParallelAgent` / `LoopAgent` |
| **适用场景** | 开放式对话、能力路由、意图识别 | 明确流程、结果可控、可审计 |
| **优势** | 灵活、上下文感知 | 稳定、可预测、易调试 |
| **风险** | LLM 可能误判路由 | 流程僵化、不适应动态需求 |

### 二、四种编排模式详解

---

#### 模式 1：委派式（`workflows/delegation.py`）

**核心机制：** 根 Agent 是一个 `LlmAgent`，拥有 `sub_agents` 和 `tools`。LLM 根据用户输入自行决定是调用工具还是委派给子 Agent。

```python
delegation_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="delegation_root",
    instruction="You are the coordinator. Delegate greetings to the greeting agent...",
    tools=[get_weather],              # 自己能用的工具
    sub_agents=[greeting_agent, farewell_agent],  # 可委派的下级
)
```

**ADK 关键概念：**
- **`sub_agents` 的路由靠 `description`**：ADK 会把每个子 Agent 的 `name` + `description` 注入根 Agent 的系统提示，LLM 据此决定是否委派。子 Agent 的 `description` 写得越精确，路由越准确。
- **工具 vs 子 Agent 的边界**：根 Agent 可以同时持有 `tools` 和 `sub_agents`。简单动作（如查天气）用工具；复杂对话（如问候流程）用子 Agent。设计时要问自己：**这个能力需要独立的 instruction 和上下文吗？** 需要就拆成子 Agent，不需要就做成工具。
- **控制权流转**：一旦委派给子 Agent，**整个对话回合的控制权转移**到子 Agent。子 Agent 完成后控制权回到根 Agent。

**本示例中的角色：**
- `delegation_root`：协调员，持有 `get_weather` 工具
- `greeting_agent`：处理问候，持有 `say_hello` 工具
- `farewell_agent`：处理告别，持有 `say_goodbye` 工具

**适用场景：** 客服系统、智能助手、意图路由器——任何"用户意图不确定，需要 LLM 自主判断交给谁"的场景。

---

#### 模式 2：串行流水线（`workflows/sequential_pipeline.py`）

**核心机制：** `SequentialAgent` 按固定顺序依次执行子 Agent，前一个完成才执行下一个。

```python
pipeline_agent = SequentialAgent(
    name="report_pipeline",
    sub_agents=[research_agent, write_agent, qa_agent],
)
```

**ADK 关键概念：**
- **`output_key` 是数据传递的核心**：每个子 Agent 设置 `output_key`，Agent 的输出会自动写入 `session.state[output_key]`。下游 Agent 通过 `instruction` 中的 `{key_name}` 模板语法读取。

  ```
  research_agent  →  output_key="research_notes"  →  state["research_notes"]
  write_agent     →  instruction 中用 {research_notes} 读取上游结果
                  →  output_key="draft_report"      →  state["draft_report"]
  qa_agent        →  instruction 中用 {draft_report} 读取上游结果
  ```

- **`SequentialAgent` 本身不是 LlmAgent**：它不调用 LLM，不做决策，仅负责"依次执行"。它是纯粹的编排容器。
- **失败行为**：如果某一步 Agent 出错，后续 Agent 仍会执行（拿到的上游数据可能为空或异常）。生产环境中需要自行添加校验逻辑。

**本示例中的流水线：**
1. `research_agent` → 对主题提取 4-6 个要点 → 写入 `research_notes`
2. `write_agent` → 基于 `{research_notes}` 生成结构化报告 → 写入 `draft_report`
3. `qa_agent` → 基于 `{draft_report}` 校验并改进 → 写入 `final_report`

**适用场景：** 任何有明确阶段的流水线——内容生产、数据处理、审批链。

---

#### 模式 3：并行研究（`workflows/parallel_research.py`）

**核心机制：** `ParallelAgent` 同时启动所有子 Agent，它们独立执行互不干扰。

```python
parallel_agent = ParallelAgent(
    name="parallel_research",
    sub_agents=[market_agent, tech_agent, risk_agent],
)
```

**ADK 关键概念：**
- **独立 `output_key` 避免写入冲突**：每个并行子 Agent 必须使用不同的 `output_key`（`market_notes` / `tech_notes` / `risk_notes`），否则后写入的会覆盖先写入的。
- **并行 ≠ 异步**：ADK 内部通过 asyncio 实现并发，但所有子 Agent 都完成后 `ParallelAgent` 才算完成。
- **无依赖约束**：`ParallelAgent` 的子 Agent 之间不能有数据依赖。如果 B 需要 A 的输出，应该用 `SequentialAgent`。

**本示例中的并行角色：**
- `market_agent` → 市场维度分析 → `market_notes`
- `tech_agent` → 技术维度分析 → `tech_notes`
- `risk_agent` → 风险维度分析 → `risk_notes`

**常见组合：** 在实际项目中，`ParallelAgent` 通常不单独使用，而是作为 `SequentialAgent` 的某一步——先并行采集，再串行汇总：

```
SequentialAgent([
    ParallelAgent([market_agent, tech_agent, risk_agent]),  # 并行采集
    summary_agent,  # 串行汇总
])
```

**适用场景：** 多维度调研、多源数据采集、独立子任务批处理。

---

#### 模式 4：循环改进（`workflows/loop_refine.py`）

**核心机制：** `LoopAgent` 在限定次数内重复执行子 Agent 序列，直到达到上限或主动退出。

```python
loop_agent = LoopAgent(
    name="refine_loop",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=3,
)
```

**ADK 关键概念：**
- **`max_iterations` 是安全阀**：防止无限循环。设为 3 意味着 critic → refiner 最多执行 3 轮。
- **`exit_loop` 的实现方式——`escalate`**：ADK 没有专门的"退出循环"API。退出是通过 `tool_context.actions.escalate = True` 实现的，这会让当前 Agent 把控制权"上升"到父级（即跳出 LoopAgent）。

  ```python
  def exit_loop(tool_context: ToolContext, reason: str = "") -> dict:
      tool_context.actions.escalate = True           # 控制权上升到父级
      tool_context.actions.skip_summarization = True  # 跳过自动摘要
      return {"status": "exiting", "reason": reason}
  ```

- **循环内的状态共享**：`critic_agent` 写入 `critique`，`refiner_agent` 读取 `{critique}` 并改进 `{draft}`，改进结果又写回 `draft`。下一轮 `critic_agent` 会读到更新后的 `draft`。这种"通过 state 传递、逐轮迭代"的模式是 ADK 循环的核心手法。

**本示例中的循环角色：**
1. `critic_agent` → 找出 draft 中的问题 → 写入 `critique`
2. `refiner_agent` → 基于 `{critique}` 改进 `{draft}` → 更新 `draft`；若无需改进则调用 `exit_loop`

**适用场景：** 自我校验、迭代优化、质量门控——任何"生成 → 评审 → 改进"的循环流程。

---

### 三、数据流：`output_key` 与 `{template}` 模式

这是贯穿所有编排模式的核心机制，值得单独强调：

```
Agent 执行完毕
    │
    ▼
output_key="xxx"  →  state["xxx"] = Agent 的输出文本
    │
    ▼
下游 Agent 的 instruction 中写 {xxx}
    │
    ▼
ADK 在运行时自动将 {xxx} 替换为 state["xxx"] 的值
```

**要点：**
- `output_key` 是写入端，`{key}` 模板是读取端
- 所有 Agent 共享同一个 `session.state` 字典
- 命名要有辨识度，避免冲突（如 `research_notes` 而非 `notes`）
- 这个机制取代了"Agent 之间显式传参"的需要

---

### 四、入口架构：`app.py` + `main.py`

**`apps/app.py` —— 路由选择层**

通过环境变量 `WORKFLOW` 选择使用哪个编排模式：

```python
WORKFLOW = os.getenv("WORKFLOW", "sequential").lower()
ROOT_AGENTS = {
    "sequential": pipeline_agent,
    "parallel": parallel_agent,
    "loop": loop_agent,
    "delegation": delegation_agent,
}
root_agent = ROOT_AGENTS.get(WORKFLOW, pipeline_agent)
app = App(name=f"orchestration_{WORKFLOW}", root_agent=root_agent)
```

这种"配置化切换根 Agent"的模式在工程中很常见——可以用于 A/B 测试、环境隔离、功能开关。

**`apps/main.py` —— 执行入口**

使用 `InMemoryRunner` 创建运行时，调用 `run_debug` 执行一次对话：

```python
runner = InMemoryRunner(app=app)
response = await runner.run_debug(prompt)
```

- `InMemoryRunner` 适合开发调试，Session/State 都在内存中，进程结束即丢失
- `run_debug` 是简化的单轮调试接口，适合快速验证流程

---

## 小结

1. **编排决定系统稳定性，优先于 prompt 微调。** prompt 再好，如果编排结构混乱，系统行为就不可预测。
2. **委派式强调灵活性，工作流式强调确定性。** 两者可以嵌套组合。
3. **`output_key` + `{template}` 是 ADK 的数据总线。** 理解这个模式就能理解所有编排中的数据流。
4. **`escalate` 是控制权上升机制。** 不仅用于退出循环，也是 ADK 中子 Agent 向父级传递控制权的通用方式。
5. **多智能体系统一定要定义清晰的输入/输出与失败边界。** 每个 Agent 应该有明确的"我输入什么、输出什么、出错了怎么办"。

---

## 流程图

详见：`phases/03-orchestration/docs/architecture.md`（包含 Mermaid 格式的四种编排流程图）

## 代码布局
```
phases/03-orchestration/
  agents/                          # 认知层：各角色 Agent
    greeting_agent.py              #   委派式 - 问候
    farewell_agent.py              #   委派式 - 告别
    research_agent.py              #   流水线 - 研究
    write_agent.py                 #   流水线 - 写作
    qa_agent.py                    #   流水线 - 质量校验
  workflows/                       # 编排层：组装 Agent 的方式
    delegation.py                  #   委派式编排
    sequential_pipeline.py         #   串行流水线
    parallel_research.py           #   并行研究（含局部 Agent 定义）
    loop_refine.py                 #   循环改进（含 exit_loop 工具）
  tools/                           # 行动层：工具函数
    basic_tools.py                 #   get_weather / say_hello / say_goodbye
  apps/                            # 入口层
    app.py                         #   WORKFLOW 路由 + App 创建
    main.py                        #   InMemoryRunner + 执行
  docs/
    architecture.md                #   整体架构与流程图
```

## 运行方式

在 `phases/03-orchestration/` 目录下：

```bash
# 串行流水线（默认）
WORKFLOW=sequential PROMPT="Write a brief report on edge AI." python apps/main.py

# 委派式
WORKFLOW=delegation PROMPT="Hello! What's the weather in Tokyo?" python apps/main.py

# 并行研究
WORKFLOW=parallel PROMPT="Analyze the current state of LLM agents." python apps/main.py

# 循环改进（需要先在 state 中有 draft，可通过修改 main.py 注入初始状态）
WORKFLOW=loop PROMPT="Improve this draft: AI agents are useful." python apps/main.py
```

可用的 `WORKFLOW`：`delegation` | `sequential` | `parallel` | `loop`
