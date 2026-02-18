# Step 6: 记忆 + 会话持久化

## 教学目标

- **Phase 06** DatabaseSessionService + FileArtifactService + InMemoryMemoryService
- **Phase 06** State 4 种作用域：session / user: / app: / temp:
- **Phase 06** search_memory 语义召回 + artifact 版本管理

## 学到什么

从 InMemoryRunner 切换到 Runner + 三个持久化 service。
实现用户偏好跨会话持久化（`user:` scope），搜索历史语义召回（`search_memory`），
报价文档版本管理（artifact）。

## 核心概念

```
Runner（非 InMemoryRunner）
  ├── DatabaseSessionService  — session + state 持久化到 SQLite
  ├── FileArtifactService     — artifact 文件版本管理
  └── InMemoryMemoryService   — 历史对话关键词搜索

State 4 种作用域：
  session scope  — state["key"]           当前会话内有效
  user: scope    — state["user:key"]      同一用户跨会话持久
  app: scope     — state["app:key"]       跨用户全局统计
  temp: scope    — state["temp:key"]      不持久化，单次调用内

search_memory(query) — 搜索历史对话（InMemoryMemoryService 用关键词匹配）
save_artifact(filename, artifact) — 保存版本化文件
load_artifact(filename, version) — 加载特定版本
```

## 创建文件清单

```
新建:
  tools/memory_tools.py           # recall_search_history, save_document
  tools/preference_tools.py       # set_preference, get_preference

修改:
  apps/main.py                    # STEP≥6 切换到 Runner + 3 个 service
  agents/orchestrator.py          # 添加 memory/preference 工具到合适的 agent
  apps/app.py                     # STEP="6"
```

## 代码实现

### apps/main.py（重写——Runner 分支）

```python
"""Phase 09 入口——Step≥6 使用 Runner + 持久化 service。

关键变化：
  InMemoryRunner → Runner
  新增三个 service：DatabaseSessionService, FileArtifactService, InMemoryMemoryService
  SQLite 数据库存储在 data/sessions.db
  Artifact 文件存储在 data/artifacts/
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STEP = int(os.getenv("STEP", "1"))

if STEP >= 6:
    # --- 持久化模式 ---
    from google.adk.runners import Runner
    from google.adk.sessions import DatabaseSessionService
    from google.adk.artifacts import FileArtifactService
    from google.adk.memory import InMemoryMemoryService
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
```

### tools/memory_tools.py

```python
"""记忆工具——历史搜索召回 + 文档保存。

search_memory: 搜索过去的对话，找到相关的采购历史
save_document: 将报价/对比文档保存为版本化 artifact
"""

from google.genai import types
from google.adk.tools import ToolContext


async def recall_search_history(query: str, tool_context: ToolContext) -> dict:
    """Search past sourcing conversations for relevant context.

    Finds related discussions from previous sessions to provide
    historical context (past searches, preferences, decisions).

    Args:
        query: Keywords to search in past conversations.
    """
    response = await tool_context.search_memory(query=query)

    if not response or not response.memories:
        return {
            "query": query,
            "found": False,
            "note": "No past sourcing conversations match this query.",
        }

    memories = []
    for memory in response.memories:
        excerpts = []
        if memory.events:
            for event in memory.events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            excerpts.append(
                                f"[{event.author}]: {part.text[:200]}"
                            )
        memories.append({
            "session_id": getattr(memory, "session_id", "unknown"),
            "excerpts": excerpts[:3],
        })

    return {
        "query": query,
        "found": True,
        "matches": len(memories),
        "memories": memories,
    }


async def save_document(
    content: str, filename: str, tool_context: ToolContext,
) -> dict:
    """Save a sourcing document as a versioned artifact.

    Artifacts are versioned — each save creates a new version.
    Use for quotes, comparison reports, requirement docs.

    Args:
        content: Document content (markdown, text, etc.).
        filename: Filename for the artifact (e.g., "quote_001.md").
    """
    part = types.Part.from_text(text=content)
    version = await tool_context.save_artifact(filename=filename, artifact=part)
    return {
        "status": "saved",
        "filename": filename,
        "version": version,
    }
```

### tools/preference_tools.py

```python
"""用户偏好工具——使用 user: scope 实现跨会话持久化。

user: 前缀的 state key 在 DatabaseSessionService 下：
  - 同一 user_id 的所有 session 共享
  - 重启应用后仍然存在

典型用途：
  - 偏好的质量标准（user:pref_quality → "ISO9001"）
  - 偏好的供应商区域（user:pref_region → "Jiangsu"）
  - 最大预算（user:pref_max_budget → "50000 CNY"）
"""

from google.adk.tools import ToolContext


def set_preference(key: str, value: str, tool_context: ToolContext) -> dict:
    """Save a sourcing preference that persists across sessions.

    Uses user: state scope — survives session restarts.

    Args:
        key: Preference name (e.g., 'quality_standard', 'preferred_region').
        value: Preference value (e.g., 'ISO9001', 'Jiangsu').
    """
    state_key = f"user:pref_{key}"
    tool_context.state[state_key] = value
    return {"saved": state_key, "value": value, "scope": "user (cross-session)"}


def get_preference(key: str, tool_context: ToolContext) -> dict:
    """Read a sourcing preference.

    Args:
        key: Preference name to look up.
    """
    state_key = f"user:pref_{key}"
    value = tool_context.state.get(state_key)
    return {
        "key": key,
        "state_key": state_key,
        "value": value,
        "found": value is not None,
    }


def list_preferences(tool_context: ToolContext) -> dict:
    """List all saved sourcing preferences."""
    prefs = {}
    for key, value in tool_context.state.items():
        if key.startswith("user:pref_"):
            short_key = key.replace("user:pref_", "")
            prefs[short_key] = value
    return {"preferences": prefs, "count": len(prefs)}
```

## State Scoping 完整示例

```python
# 工具函数中使用不同 scope
def example_tool(tool_context: ToolContext):
    # Session scope — 当前会话
    tool_context.state["catalog_results"] = [...]

    # User scope — 跨会话持久化
    tool_context.state["user:pref_quality"] = "ISO9001"

    # App scope — 跨用户统计
    tool_context.state["app:total_searches"] = 42

    # Temp scope — 不持久化
    tool_context.state["temp:timer_start"] = time.time()
```

| Scope | 前缀 | 持久化 | 共享范围 | 典型用途 |
|-------|------|--------|---------|---------|
| session | 无 | 是 | 当前会话 | 搜索结果、需求 |
| user: | `user:` | 是 | 同一用户 | 偏好、历史 |
| app: | `app:` | 是 | 全局 | 统计、配置 |
| temp: | `temp:` | 否 | 单次调用 | 计时器、临时变量 |

## 验证

```bash
cd phases/09-capstone

# 设置偏好（user: scope 持久化）
STEP=6 PROMPT="Remember that I prefer ISO9001 certified suppliers" python apps/main.py
# 期望：state 中出现 user:pref_quality_standard = ISO9001

# 新会话中偏好仍在
STEP=6 PROMPT="What are my sourcing preferences?" python apps/main.py
# 期望：list_preferences 返回之前保存的偏好

# 搜索 + 文档保存
STEP=6 PROMPT="Find steel sheets and save the results as a report" python apps/main.py
# 期望：save_document 创建 artifact，输出 version 号
```

## 你应该理解的

1. `InMemoryRunner` 只用于开发调试，`Runner` 才能接入持久化 service
2. `DatabaseSessionService` 使用 SQLAlchemy + aiosqlite → session + state 持久化
3. `user:` 前缀的 state key 跨 session 共享 → 适合用户偏好
4. `search_memory()` 搜索**历史对话内容** → InMemoryMemoryService 用关键词匹配
5. `save_artifact` 每次调用创建新版本 → 天然版本管理
6. `temp:` scope 永不持久化 → 安全地存放临时数据
