from google.adk.tools import ToolContext
from google.genai import types


async def save_report_draft(
    content: str,
    filename: str = "report_draft.md",
    tool_context: ToolContext = None,
) -> dict:
    """Save a report draft as an artifact for version tracking.

    Args:
        content: The report content to save.
        filename: The filename for the artifact.
    """
    if not content.strip():
        return {"error": "Content cannot be empty."}

    # --- ToolContext: save as versioned artifact ---
    artifact = types.Part.from_text(text=content)
    version = await tool_context.save_artifact(filename=filename, artifact=artifact)

    # --- ToolContext: track in state ---
    tool_context.state["last_saved_file"] = filename
    tool_context.state["last_saved_version"] = version

    # --- Skip summarization: return raw result without LLM re-interpretation ---
    tool_context.actions.skip_summarization = True

    return {
        "status": "saved",
        "filename": filename,
        "version": version,
    }
