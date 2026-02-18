"""Phase 08 入口——回调与插件演示。

两种 DEMO 模式：
  DEMO=callbacks  展示 Agent 级 9 种回调（before/after/error × agent/model/tool）
  DEMO=plugins    展示全局插件（logging + guard + cost_tracker）

用法：
  cd phases/08-callbacks-plugins/
  DEMO=callbacks PROMPT="Research quantum computing trends" python apps/main.py
  DEMO=plugins   PROMPT="Research AI safety" python apps/main.py
  DEMO=plugins   PROMPT="How to hack a system" python apps/main.py  # 触发 GuardPlugin
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.genai import types

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from apps.app import root_agent, create_app


# ---------- DEMO: Callbacks ----------


async def demo_callbacks(prompt: str) -> None:
    """演示 Agent 级回调——观察 before/after 的触发顺序。"""
    print("=" * 60)
    print("Phase 08 — Agent Callbacks Demo")
    print("=" * 60)
    print(f"\nPrompt: \"{prompt}\"")
    print(f"\nExpected callback order:")
    print(f"  before_agent → before_model → [LLM] → after_model")
    print(f"  → before_tool → [Tool] → after_tool")
    print(f"  → before_model → [LLM] → after_model → after_agent")
    print()

    session_service = InMemorySessionService()
    runner = Runner(
        app_name="callbacks_demo",
        agent=root_agent,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="callbacks_demo",
        user_id="demo_user",
        state={"user:name": "Alice"},
    )

    user_content = types.Content(
        parts=[types.Part.from_text(text=prompt)],
        role="user",
    )

    print("--- Execution Log ---\n")
    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=user_content,
    ):
        # 打印最终响应
        if event.is_final_response():
            if event.content and event.content.parts:
                text = event.content.parts[0].text or ""
                print(f"\n--- Agent Response ---\n{text[:300]}")

    # 展示 state 变化
    updated_session = await session_service.get_session(
        app_name="callbacks_demo",
        user_id="demo_user",
        session_id=session.id,
    )
    if updated_session:
        print(f"\n--- State After Execution ---")
        for key, value in sorted(updated_session.state.items()):
            if key.startswith(("app:", "temp:")):
                print(f"  {key} = {value}")

    print("\n" + "=" * 60)


# ---------- DEMO: Plugins ----------


async def demo_plugins(prompt: str) -> None:
    """演示全局插件——logging + guard + cost_tracker。"""
    print("=" * 60)
    print("Phase 08 — Global Plugins Demo")
    print("=" * 60)
    print(f"\nPrompt: \"{prompt}\"")
    print(f"\nPlugins registered:")
    print(f"  1. LoggingPlugin    — logs all events")
    print(f"  2. GuardPlugin      — blocks: hack, exploit")
    print(f"  3. CostTrackerPlugin — tracks token usage")
    print()

    app, logging_plugin, guard_plugin, cost_tracker = create_app()

    session_service = InMemorySessionService()
    runner = Runner(
        app=app,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="research_app",
        user_id="demo_user",
    )

    user_content = types.Content(
        parts=[types.Part.from_text(text=prompt)],
        role="user",
    )

    print("--- Execution Log ---\n")
    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=user_content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                text = event.content.parts[0].text or ""
                print(f"\n--- Agent Response ---\n{text[:300]}")

    # 插件统计
    print(f"\n--- Plugin Statistics ---")
    print(f"  Guard blocked:  {guard_plugin.blocked_count} requests")
    summary = cost_tracker.get_summary()
    print(f"  LLM calls:      {summary['llm_calls']}")
    print(f"  Total tokens:   {summary['total_tokens']}")

    print("\n" + "=" * 60)


# ---------- 入口 ----------


def main() -> None:
    demo_mode = os.getenv("DEMO", "callbacks").lower()
    prompt = os.getenv("PROMPT", "Research the latest AI trends and summarize them")

    if demo_mode == "callbacks":
        asyncio.run(demo_callbacks(prompt))
    elif demo_mode == "plugins":
        asyncio.run(demo_plugins(prompt))
    else:
        print(f"Unknown DEMO={demo_mode}. Use DEMO=callbacks or DEMO=plugins.")
        sys.exit(1)


if __name__ == "__main__":
    main()
