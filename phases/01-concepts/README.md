# 1.1 认识 ADK（概念与定位）

## 编写
ADK 的心智模型可以拆成四层：编排层、认知层、行动层、记忆层。  
编排层负责“谁在什么时候做什么”，典型载体是 Runner 与工作流结构。  
认知层是 Agent 的思考与决策。  
行动层由 Tool 承载，负责真正的副作用或外部能力调用。  
记忆层由 Session/State 以及持久化策略承载，决定 agent 的连续性与可复用性。

## 讲解
这个四层模型可以帮助你把“多智能体协作、工具调用、记忆”统一到一个工程化框架中。  
你不需要纠结具体 API 细节，先把边界划清楚：  
编排解决协作，工具解决动作，记忆解决长期一致性，认知解决策略与质量。

## 小结
- ADK 本质是工程化的 agent 运行时与编排框架。
- 先记住四层模型，后续每个模块都能对应到其中一层。
- 学习顺序按“编排 → 工具 → 记忆 → 产物 → 评估”最有效。

## 代码示意（概念层最小骨架）

文件：`phases/01-concepts/agent.py`
```python
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App


def remember_topic(topic: str, tool_context) -> dict:
    """Store a temporary topic for this invocation in session state."""
    tool_context.state["temp:topic"] = topic
    return {"topic": topic}


root_agent = Agent(
    model="gemini-2.5-flash",
    name="concept_agent",
    description="Demonstrates ADK's four-layer model.",
    instruction=(
        "You are a concise assistant. "
        "When a user mentions a topic, call remember_topic. "
        "Use tools for actions and keep answers short."
    ),
    tools=[remember_topic],
)

app = App(
    name="concept_app",
    root_agent=root_agent,
)
```

文件：`phases/01-concepts/main.py`
```python
import asyncio

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner

from agent import app

load_dotenv()

runner = InMemoryRunner(app=app)


async def main() -> None:
    # run_debug requires ADK Python v1.18+
    response = await runner.run_debug(
        "Hello ADK. Remember this topic: multi-agent orchestration."
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
```

## 说明
- `Agent` 体现认知层，`remember_topic` 体现行动层，`tool_context.state` 体现记忆层。
- `App + Runner` 负责编排与运行时生命周期。

