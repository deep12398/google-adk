from google.adk.tools import FunctionTool, ToolContext


def publish_report(
    filename: str,
    destination: str = "public",
    tool_context: ToolContext = None,
) -> dict:
    """Publish a report to the specified destination. This is a destructive action.

    Args:
        filename: The report file to publish.
        destination: Where to publish ('public', 'internal', 'archive').
    """
    valid_destinations = {"public", "internal", "archive"}
    if destination not in valid_destinations:
        return {"error": f"Invalid destination. Must be one of: {valid_destinations}"}

    return {
        "status": "published",
        "filename": filename,
        "destination": destination,
    }


def delete_report(
    filename: str,
    tool_context: ToolContext = None,
) -> dict:
    """Permanently delete a report. Cannot be undone.

    Args:
        filename: The report file to delete.
    """
    return {"status": "deleted", "filename": filename}


# --- Approach 1: Static confirmation (always requires) ---
publish_tool = FunctionTool(publish_report, require_confirmation=True)


# --- Approach 2: Conditional confirmation (only for 'public') ---
def _needs_confirmation(**kwargs) -> bool:
    return kwargs.get("destination") == "public"


publish_tool_conditional = FunctionTool(
    publish_report, require_confirmation=_needs_confirmation
)

# --- Approach 3: Always-confirm delete ---
delete_tool = FunctionTool(delete_report, require_confirmation=True)
