# 1.3 多智能体编排（重点）

## 编写
多智能体编排的核心是“任务分解 + 责任边界”。  
本阶段展示两类编排方式：
1) **委派式**：由一个根 Agent 基于描述与指令把任务委派给子 Agent。  
2) **工作流式**：用确定性流程（串行/并行/循环）编排多 Agent。

## 讲解
- 委派式适合“开放式对话 + 能力路由”的场景。
- 工作流式适合“明确流程 + 结果可控”的场景。

为了让差异清晰，本阶段提供 4 个可切换的编排示例：
- `delegation`：根 Agent + 子 Agent 自动委派
- `sequential`：研究 → 写作 → QA
- `parallel`：并行研究
- `loop`：批判 → 改写（迭代）

## 小结
- 编排决定系统稳定性，优先于 prompt 微调。
- 委派式强调灵活性，工作流式强调确定性。
- 多智能体系统一定要定义清晰输入/输出与失败边界。

## 代码布局
```
phases/03-orchestration/
  agents/
    greeting_agent.py
    farewell_agent.py
    research_agent.py
    write_agent.py
    qa_agent.py
  workflows/
    delegation.py
    sequential_pipeline.py
    parallel_research.py
    loop_refine.py
  tools/
    basic_tools.py
  apps/
    app.py
    main.py
  docs/
```

## 运行方式
在该阶段目录下运行（示例）：
```
WORKFLOW=sequential PROMPT="Write a brief report on edge AI." \
python apps/main.py
```

可用的 `WORKFLOW`：`delegation` | `sequential` | `parallel` | `loop`
