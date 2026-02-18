"""Phase 09 入口——Step≥6 使用 Runner + 持久化 service。

关键变化：
  Step 1-5: InMemoryRunner（内存，程序关了就丢）
  Step 6+:  Runner + DatabaseSessionService + FileArtifactService + InMemoryMemoryService
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STEP = int(os.getenv("STEP", "1"))

if STEP >= 6:
    # --- 持久化模式 ---
    from google.adk.artifacts import FileArtifactService
    from google.adk.memory import InMemoryMemoryService
    from google.adk.runners import Runner
    from google.adk.sessions import DatabaseSessionService

    from app import app

    DATA_DIR = Path(__file__).resolve().parents[1] / "data"
    DATA_DIR.mkdir(exist_ok=True)

    session_service = DatabaseSessionService(
        db_url=f"sqlite+aiosqlite:///{DATA_DIR / 'sessions.db'}",
    )
    artifact_service = FileArtifactService(
        root_dir=str(DATA_DIR / "artifacts"),
    )
    memory_service = InMemoryMemoryService()

    runner = Runner(
        app=app,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
    )

else:
    # --- 内存模式（Step 1-5）---
    from google.adk.runners import InMemoryRunner

    from app import app

    runner = InMemoryRunner(app=app)
    session_service = None


async def main() -> None:
    prompt = os.getenv("PROMPT", "I need stainless steel sheets")
    events = await runner.run_debug(prompt)

    # Step≥6：展示持久化状态
    if session_service and STEP >= 6:
        session = await session_service.get_session(
            app_name=app.name,
            user_id="debug_user_id",
            session_id="debug_session_id",
        )
        if session and session.state:
            print("\n--- Persisted State ---")
            for key, value in sorted(session.state.items()):
                scope = (
                    "temp" if key.startswith("temp:") else
                    "user" if key.startswith("user:") else
                    "app" if key.startswith("app:") else "session"
                )
                print(f"  [{scope}] {key} = {value}")


if __name__ == "__main__":
    asyncio.run(main())
