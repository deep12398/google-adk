"""State 四种作用域演示工具。

ADK State 支持四种前缀，决定数据的生命周期和共享范围：
  - 无前缀  → session scope：仅当前 session 可见，持久化到 session 存储
  - user:   → user scope：同一 user_id 的所有 session 共享
  - app:    → app scope：同一 app 的所有用户共享
  - temp:   → temp scope：仅当前 invocation 可见，永不持久化

底层机制：
  _session_util.py:extract_state_delta() 在持久化时按前缀拆分，
  写入 session_state / user_state / app_state，temp: 前缀的直接丢弃。
"""

from google.adk.tools import ToolContext


def set_user_preference(key: str, value: str, tool_context: ToolContext) -> dict:
    """设置用户偏好（user: scope，跨 session 共享）。

    Args:
        key: 偏好名称，如 language、theme。
        value: 偏好值，如 Chinese、dark。
    """
    state_key = f"user:{key}"
    tool_context.state[state_key] = value
    return {
        "status": "saved",
        "scope": "user",
        "key": state_key,
        "value": value,
        "note": "This preference persists across sessions for the same user.",
    }


def get_user_preference(key: str, tool_context: ToolContext) -> dict:
    """读取用户偏好。

    Args:
        key: 偏好名称。
    """
    state_key = f"user:{key}"
    value = tool_context.state.get(state_key)
    return {
        "key": state_key,
        "value": value,
        "found": value is not None,
    }


def increment_app_counter(counter_name: str, tool_context: ToolContext) -> dict:
    """递增全局计数器（app: scope，所有用户共享）。

    Args:
        counter_name: 计数器名称，如 total_requests、total_searches。
    """
    state_key = f"app:{counter_name}"
    current = tool_context.state.get(state_key, 0)
    new_value = current + 1
    tool_context.state[state_key] = new_value
    return {
        "scope": "app",
        "key": state_key,
        "old_value": current,
        "new_value": new_value,
        "note": "This counter is shared across all users and sessions.",
    }


def get_app_stats(tool_context: ToolContext) -> dict:
    """读取应用级统计数据（app: scope）。"""
    stats = {}
    for key, value in tool_context.state.items():
        if isinstance(key, str) and key.startswith("app:"):
            stats[key] = value
    return {
        "scope": "app",
        "stats": stats if stats else {"note": "No app-level stats found."},
    }


def save_session_note(content: str, tool_context: ToolContext) -> dict:
    """保存会话笔记（session scope，仅当前 session 可见）。

    Args:
        content: 笔记内容。
    """
    notes = list(tool_context.state.get("session_notes", []))
    notes.append(content)
    tool_context.state["session_notes"] = notes
    return {
        "scope": "session",
        "key": "session_notes",
        "total_notes": len(notes),
        "note": "Session notes persist within this session only.",
    }


def use_temp_scratch(data: str, tool_context: ToolContext) -> dict:
    """使用临时暂存区（temp: scope，永不持久化）。

    Args:
        data: 临时数据。
    """
    tool_context.state["temp:scratch"] = data
    return {
        "scope": "temp",
        "key": "temp:scratch",
        "value": data,
        "note": "This data exists only during the current invocation and is never persisted.",
    }


def show_all_state(tool_context: ToolContext) -> dict:
    """展示当前所有 state（按 scope 分类）。"""
    result = {"user": {}, "app": {}, "session": {}, "temp": {}}
    for key, value in tool_context.state.items():
        if not isinstance(key, str):
            continue
        if key.startswith("user:"):
            result["user"][key] = value
        elif key.startswith("app:"):
            result["app"][key] = value
        elif key.startswith("temp:"):
            result["temp"][key] = value
        else:
            result["session"][key] = value
    return result
