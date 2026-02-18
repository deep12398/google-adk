"""Phase 06 入口——首次使用 Runner（非 InMemoryRunner）。

关键变化：
  InMemoryRunner 硬编码了 InMemory* 三件套，无法注入自定义 service。
  本阶段使用基类 Runner，显式传入三个持久化 service：

  - DatabaseSessionService → session + state 持久化到 SQLite（通过 SQLAlchemy）
  - FileArtifactService    → artifact 版本管理到文件系统
  - InMemoryMemoryService  → 关键词搜索历史对话（开发用）

  run_debug() 定义在 Runner 基类上，可直接使用。
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import FileArtifactService
from google.adk.memory import InMemoryMemoryService

from app import app

load_dotenv()

# ---------- 持久化 service 配置 ----------

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)

# Session + State 持久化（SQLAlchemy 异步后端，使用 aiosqlite 驱动）
session_service = DatabaseSessionService(
    db_url=f"sqlite+aiosqlite:///{DATA_DIR / 'sessions.db'}",
)

# Artifact 版本管理（文件系统存储）
artifact_service = FileArtifactService(
    root_dir=str(DATA_DIR / "artifacts"),
)

# Memory 搜索（开发用：关键词匹配）
memory_service = InMemoryMemoryService()

# ---------- Runner（非 InMemoryRunner）----------

runner = Runner(
    app=app,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
)


async def main() -> None:
    prompt = os.getenv(
        "PROMPT",
        "Set my preferred language to Chinese, then search for AI trends.",
    )
    events = await runner.run_debug(prompt)

    # 展示事件数量
    print(f"\n--- Total events: {len(events)} ---")

    # 展示最终 state
    session = await session_service.get_session(
        app_name=app.name,
        user_id="debug_user_id",
        session_id="debug_session_id",
    )
    if session and session.state:
        print("\n--- Final State ---")
        for key, value in sorted(session.state.items()):
            scope = "temp" if key.startswith("temp:") else \
                    "user" if key.startswith("user:") else \
                    "app" if key.startswith("app:") else "session"
            print(f"  [{scope}] {key} = {value}")


if __name__ == "__main__":
    asyncio.run(main())
