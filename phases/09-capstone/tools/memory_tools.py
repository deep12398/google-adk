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
