import logging
from datetime import datetime, timezone
from typing import Any, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger("tool_callbacks")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s"
)


# ---------- before_tool_callback ----------
# Signature: (tool, args, tool_context) -> Optional[dict]
# Return None → proceed with execution
# Return dict → short-circuit (skip execution, use dict as result)


def log_and_validate_before(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
) -> Optional[dict]:
    """Log every tool call and block dangerous inputs."""
    logger.info(f"[BEFORE] Tool={tool.name}, Args={args}")

    # Example: block queries containing forbidden terms
    query = args.get("query", "")
    blocked_terms = ["hack", "exploit", "bypass"]
    for term in blocked_terms:
        if term in query.lower():
            logger.warning(
                f"[BLOCKED] Tool={tool.name} blocked due to term: {term}"
            )
            return {"error": f"Query contains blocked term: '{term}'"}

    # Track invocation count in state
    key = f"tool_call_count:{tool.name}"
    count = tool_context.state.get(key, 0) + 1
    tool_context.state[key] = count

    return None  # Proceed with execution


# ---------- after_tool_callback ----------
# Signature: (tool, args, tool_context, result) -> Optional[dict]
# Return None → use original result
# Return dict → replace the result


def audit_after(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    result: dict,
) -> Optional[dict]:
    """Log the tool result and add audit metadata."""
    logger.info(
        f"[AFTER] Tool={tool.name}, "
        f"Result keys={list(result.keys()) if isinstance(result, dict) else type(result)}"
    )

    # Enrich result with audit trail
    if isinstance(result, dict):
        result["_audit"] = {
            "tool": tool.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return result


# ---------- on_tool_error_callback ----------
# Signature: (tool, args, tool_context, error) -> Optional[dict]
# Return None → re-raise the exception
# Return dict → use as graceful fallback result


def handle_tool_error(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> Optional[dict]:
    """Gracefully handle tool errors instead of crashing."""
    logger.error(f"[ERROR] Tool={tool.name}, Error={error}")

    # Track error count
    key = f"tool_error_count:{tool.name}"
    count = tool_context.state.get(key, 0) + 1
    tool_context.state[key] = count

    return {
        "error": str(error),
        "fallback": True,
        "suggestion": "The service is temporarily unavailable. Please try again.",
    }
