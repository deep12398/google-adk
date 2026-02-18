"""Memory 搜索工具。

ADK Memory 系统：
  - add_session_to_memory(session) → 将 session 中的对话存入记忆库
  - search_memory(query) → 关键词/语义搜索历史对话

InMemoryMemoryService 使用简单关键词匹配（开发用）。
VertexAiRagMemoryService 使用语义向量搜索（生产用）。

ToolContext.search_memory(query) 封装了底层调用，
自动填入 app_name 和 user_id。
"""

from google.adk.tools import ToolContext


async def recall_past_research(query: str, tool_context: ToolContext) -> dict:
    """搜索历史研究记忆。

    在之前的 session 对话中搜索相关内容，用于参考或延续之前的工作。

    Args:
        query: 搜索关键词。
    """
    response = await tool_context.search_memory(query=query)

    if not response or not response.memories:
        return {
            "query": query,
            "found": False,
            "note": "No past research found matching this query.",
        }

    memories = []
    for memory in response.memories:
        events_text = []
        if memory.events:
            for event in memory.events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            events_text.append(
                                f"[{event.author}]: {part.text[:200]}"
                            )
        memories.append({
            "session_id": getattr(memory, "session_id", "unknown"),
            "excerpts": events_text[:5],
        })

    return {
        "query": query,
        "found": True,
        "matches": len(memories),
        "memories": memories,
    }
