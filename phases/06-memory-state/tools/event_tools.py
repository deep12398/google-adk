"""Event Sourcing 查看工具。

ADK 中所有 state 变更都通过 Event.actions.state_delta 记录。
Event 是不可变的，形成了完整的变更历史（Event Sourcing）。

通过遍历 session.events，可以：
  - 看到每个 state 变更的来源（哪个 agent/工具触发的）
  - 看到变更时间戳
  - 看到 artifact 版本变化（artifact_delta）
  - 审计完整的状态演变过程
"""

from google.adk.tools import ToolContext


def inspect_state_changes(tool_context: ToolContext) -> dict:
    """查看当前 session 中所有 state 变更的历史。

    遍历 session events，提取每个 event 的 state_delta，
    展示 state 是如何一步步演变的。
    """
    session = tool_context.session
    if not session or not session.events:
        return {"changes": [], "note": "No events in current session."}

    changes = []
    for event in session.events:
        if not event.actions:
            continue

        entry = {}

        if event.actions.state_delta:
            entry["type"] = "state_change"
            entry["author"] = event.author
            entry["timestamp"] = event.timestamp
            entry["state_delta"] = dict(event.actions.state_delta)

        if event.actions.artifact_delta:
            entry.setdefault("type", "artifact_change")
            entry["author"] = event.author
            entry["timestamp"] = event.timestamp
            entry["artifact_delta"] = dict(event.actions.artifact_delta)

        if entry:
            changes.append(entry)

    return {
        "total_events": len(session.events),
        "state_changes": len(changes),
        "changes": changes,
    }


def get_session_info(tool_context: ToolContext) -> dict:
    """获取当前 session 的基本信息。"""
    session = tool_context.session
    if not session:
        return {"error": "No active session."}

    return {
        "session_id": session.id,
        "app_name": session.app_name,
        "user_id": session.user_id,
        "event_count": len(session.events) if session.events else 0,
        "state_keys": list(session.state.keys()) if session.state else [],
    }
