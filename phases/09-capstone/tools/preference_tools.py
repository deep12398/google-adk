"""用户偏好工具——使用 user: scope 实现跨会话持久化。

user: 前缀的 state key 在 DatabaseSessionService 下：
  - 同一 user_id 的所有 session 共享
  - 重启应用后仍然存在
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
