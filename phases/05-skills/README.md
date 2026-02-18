# 1.5 技能复用与渐进加载

## 编写

Phase 03-04 中，所有工具都是"全量注册"的——不管 Agent 这次用不用，每次 LLM 调用都带上全部工具的完整 schema。10 个工具就是 10 份定义，每轮对话都重复发送。

**从 ADK 源码看发生了什么：**

```
_preprocess_async()           ← 每次 LLM 调用前执行
  → 遍历 agent.tools
  → 对每个 tool 调用 _get_declaration() 生成 FunctionDeclaration
  → 全部塞进 llm_request.config.tools
  → generate_content(config=config)  ← 带着全部工具定义发给 LLM
```

没有缓存，没有去重，没有按需加载。

**Claude 的 Agent Skills 给出了一个解法：渐进加载（Progressive Disclosure）。** Skill 分三层：
- **元数据层**（name + description）：始终可见，~100 tokens，用于路由
- **指令层**（instruction）：激活后才加载
- **工具层**（tools）：激活后才注册到 LLM 请求

本阶段在 ADK 中实现这个理念，同时覆盖 5 个 ADK 能力：

| 序号 | 能力 | ADK 载体 | 本阶段示例 |
|:---:|------|----------|-----------|
| 1 | 动态 Prompt | `InstructionProvider`（Callable） | `skills/loader.py` |
| 2 | 工具集封装 | 自定义 `BaseToolset` 子类 | `skills/loader.py` |
| 3 | Agent 克隆 | `agent.clone(update={...})` | `agents/specialists.py` |
| 4 | 技能包与渐进加载 | Skill dataclass + SkillAwareToolset | `skills/` 目录 |
| 5 | 上下文隔离 | `include_contents="none"` | `agents/report_agent.py` |

---

## 讲解

### 一、什么是 Skill（技能包）

Skill **不是** Agent 工厂。Skill 是一个独立的数据对象，包含三层信息：

```python
@dataclass
class Skill:
    name: str           # 元数据层：标识
    description: str    # 元数据层：短描述，用于路由
    instruction: str    # 指令层：完整操作指南
    tools: list         # 工具层：关联的工具函数
```

类比：
- **Tool** = 一把刀（执行能力）
- **Skill** = 一本菜谱（操作知识）+ 它需要的厨具清单
- **Agent** = 厨师（运行载体）

Skill 可以独立存在，不绑定任何 Agent。同一个 Skill 可以被多个 Agent 装载。

---

### 二、渐进加载——核心机制

通过两个组件配合实现：

#### SkillAwareToolset（BaseToolset 子类）

```python
class SkillAwareToolset(BaseToolset):
    async def get_tools(self, readonly_context=None):
        tools = [self._activate_tool]  # 始终提供 activate_skill
        if readonly_context:
            active = readonly_context.state.get("active_skills", [])
            for name in active:
                skill = self._registry.get_skill(name)
                if skill:
                    tools.extend(skill 的工具)
        return tools
```

关键：ADK 在**每次 LLM 调用前**都会调 `get_tools()`。当 `activate_skill` 往 state 写入已激活技能后，下一次 `get_tools()` 就会返回新工具。

#### make_skill_instruction（InstructionProvider）

```python
def provider(ctx) -> str:
    active = ctx.state.get("active_skills", [])
    if not active:
        return "可用技能目录：\n" + catalog + "\n请先激活技能"
    else:
        return "已激活技能指令：\n" + 完整指令
```

#### 完整流程

```
LLM 调用 #1:
  get_tools() → [activate_skill]         ← 只有 1 个工具
  instruction → 技能目录（元数据层）       ← 只有 name + description
  LLM 回复: "我需要 research 技能"
  → 调用 activate_skill("research")
  → state["active_skills"] = ["research"]

LLM 调用 #2:
  get_tools() → [activate_skill, search_web, summarize_text]  ← 工具出现了
  instruction → 研究技能完整指令（指令层）                       ← 指令也出现了
  LLM 使用 search_web 开始工作
```

**Token 节省：** 如果注册了 5 个技能共 10 个工具，传统方式每次发 10 个工具定义。渐进加载只发 activate_skill + 已激活技能的工具。

---

### 三、InstructionProvider——两种 instruction 方式

| | 字符串模板 | Callable（InstructionProvider） |
|---|---|---|
| **语法** | `"Research {topic}"` | `def provider(ctx) -> str:` |
| **State 注入** | ADK 自动替换 `{state_key}` | 手动读 `ctx.state`，ADK 不替换 |
| **适用场景** | 固定格式 + 简单替换 | 条件分支、动态生成 |
| **本阶段用法** | report_agent 的 instruction | skilled_agent 的 instruction |

report_agent 用字符串模板，因为它只需要固定地从 state 读三个 key：

```python
instruction = "...\n{tech_researcher_notes}\n{market_researcher_notes}\n..."
```

skilled_agent 用 callable，因为它需要根据 active_skills 动态决定返回什么指令。

---

### 四、apply_skill 与 clone()

Skill 是数据，Agent 是载体。`apply_skill()` 把技能包装载到 Agent 上：

```python
def apply_skill(skill: Skill, name: str) -> LlmAgent:
    return LlmAgent(
        instruction=skill.instruction,
        tools=skill.tools,
        ...
    )

tech_researcher = apply_skill(tech_skill, "tech_researcher")
```

当只需要改几个字段时，`clone()` 更简洁：

```python
market_researcher = base.clone(update={
    "name": "market_researcher",
    "instruction": market_skill.instruction,
})
```

| | apply_skill | clone() |
|---|---|---|
| **输入** | Skill 数据对象 | 已有 Agent 实例 |
| **适合** | 差异较大的场景 | 只改 1-2 个字段 |
| **语义** | "装载技能包" | "从模板派生变体" |

---

### 五、include_contents——上下文隔离

```python
report_agent = LlmAgent(
    include_contents="none",   # 不接收对话历史
    instruction="...\n{tech_researcher_notes}\n...",  # 只从 state 读数据
)
```

| 值 | Agent 看到什么 |
|---|---|
| `"default"` | 完整对话历史 + state 模板替换 |
| `"none"` | 无对话历史，只有 instruction（其中 `{key}` 被替换为 state 值） |

适用于汇总角色：不需要知道对话过程，只需要结构化结果。节省 token，避免干扰。

---

## 小结

1. **Skill 是知识包，不是 Agent 工厂。** 独立于 Agent 存在，可被多个 Agent 装载和组合。
2. **渐进加载是核心创新。** 利用 ADK `get_tools()` 每次请求重新调用的机制，实现按需注册工具。未激活的技能只占元数据的 token。
3. **InstructionProvider 让 prompt 随激活状态动态变化。** callable 和字符串模板各有适用场景，不能混用。
4. **apply_skill 装载技能，clone() 派生变体。** 前者强调技能与 Agent 解耦，后者适合小改动。
5. **include_contents="none" 隔离上下文。** 汇总 Agent 只看结构化数据，不看对话过程。

---

## 代码布局

```
phases/05-skills/
  prompts/
    templates.py                 # 共享 prompt 片段（跨 Skill 复用）
  tools/
    search_tool.py               # search_web + summarize_text 函数
  skills/                        # 技能包系统
    base.py                      #   Skill dataclass + SkillRegistry
    loader.py                    #   SkillAwareToolset + make_skill_instruction
    research.py                  #   通用研究技能（search_web + summarize_text）
    summary.py                   #   摘要技能（纯 LLM，无工具）
    domain_skills.py             #   科技/市场/法规 三个领域技能
  agents/
    skilled_agent.py             #   渐进加载 agent（单领域用）
    specialists.py               #   apply_skill vs clone() 两种方式
    report_agent.py              #   include_contents="none" 隔离
  workflows/
    multi_domain_research.py     #   并行多领域 → 汇总
    single_research.py           #   单领域（渐进加载 demo）
  apps/
    app.py                       #   DEMO 路由
    main.py                      #   执行入口
  docs/
    architecture.md              #   架构图
```

## 运行方式

```bash
cd phases/05-skills/

# 单领域研究（渐进加载 demo：observe activate_skill → tools appear）
DEMO=single PROMPT="Research the latest in quantum computing." python apps/main.py

# 多领域并行研究 → 汇总报告
DEMO=multi PROMPT="Research AI governance across tech, market, and legal domains." python apps/main.py
```
