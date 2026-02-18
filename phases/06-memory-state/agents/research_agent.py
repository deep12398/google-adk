"""研究 Agent——使用 state scope + research_tools。

演示要点：
  1. 使用 search_web 时自动追踪 app:total_searches（app scope）
  2. 搜索历史写入 session scope
  3. 用户偏好通过 user: scope 跨 session 共享
  4. 临时数据用 temp: scope
  5. output_key 将研究结果写入 state，供下游 agent 使用
"""

from google.adk.agents import LlmAgent

from tools.state_tools import (
    set_user_preference,
    get_user_preference,
    increment_app_counter,
    get_app_stats,
    save_session_note,
    use_temp_scratch,
    show_all_state,
)
from tools.research_tools import search_web, summarize_findings
from tools.event_tools import inspect_state_changes, get_session_info

research_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="research_agent",
    instruction=(
        "You are a research assistant with full state management capabilities.\n\n"
        "## Your Tools\n"
        "- **search_web**: Search for information (auto-tracks search count)\n"
        "- **summarize_findings**: Create a structured summary of research\n"
        "- **set_user_preference / get_user_preference**: Manage user preferences "
        "(persists across sessions)\n"
        "- **increment_app_counter / get_app_stats**: Track app-level metrics "
        "(shared across all users)\n"
        "- **save_session_note**: Save notes within this session\n"
        "- **use_temp_scratch**: Temporary scratch space (never persisted)\n"
        "- **show_all_state**: Display all state organized by scope\n"
        "- **inspect_state_changes / get_session_info**: View event history\n\n"
        "## Workflow\n"
        "1. If the user mentions preferences (language, theme, etc.), "
        "save them with set_user_preference.\n"
        "2. For research tasks, use search_web then summarize_findings.\n"
        "3. Use save_session_note to record key insights.\n"
        "4. When asked about state or history, use show_all_state or "
        "inspect_state_changes.\n"
        "5. Always increment_app_counter('total_requests') at the start.\n"
    ),
    tools=[
        search_web,
        summarize_findings,
        set_user_preference,
        get_user_preference,
        increment_app_counter,
        get_app_stats,
        save_session_note,
        use_temp_scratch,
        show_all_state,
        inspect_state_changes,
        get_session_info,
    ],
    output_key="research_output",
)
