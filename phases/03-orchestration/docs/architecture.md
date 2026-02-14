# 多智能体编排：整体架构说明

本阶段展示两类编排形态：委派式与工作流式，并用统一入口进行切换。

## 组件与职责
- `apps/app.py`：读取 `WORKFLOW` 环境变量，选择根 Agent。
- `apps/main.py`：创建 Runner 并执行一次对话。
- `workflows/`：编排层，定义委派、串行、并行、循环等结构。
- `agents/`：认知层，具体任务角色（研究、写作、QA、问候/告别）。
- `tools/`：行动层，提供可调用的工具函数。

## 四种编排示例
1) 委派式（`delegation.py`）
- 根 Agent 拥有 `sub_agents`，用于处理问候与告别。
- 天气问题由根 Agent 直接调用工具。

2) 串行流水线（`sequential_pipeline.py`）
- `SequentialAgent` 固定顺序执行：Research → Write → QA。
- 通过 `output_key` 将中间结果写入共享状态，供下游读取。

3) 并行研究（`parallel_research.py`）
- `ParallelAgent` 同时运行多个研究 Agent。
- 每个 Agent 写入独立的 state key，避免覆盖。

4) 循环改进（`loop_refine.py`）
- `LoopAgent` 在限定次数内循环 Critic → Refiner。
- Refiner 可调用 `exit_loop` 提前终止。

## 运行入口
- `WORKFLOW=delegation|sequential|parallel|loop`
- `PROMPT=...`
- 执行：`python apps/main.py`

## 关系图（文字版）
- apps 负责加载 workflow
- workflow 负责组织 agents
- agents 使用 tools
- state 在 agents 之间传递

