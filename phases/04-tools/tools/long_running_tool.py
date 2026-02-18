import asyncio

from google.adk.tools import LongRunningFunctionTool, ToolContext


async def generate_pdf_report(
    content: str,
    format: str = "pdf",
    tool_context: ToolContext = None,
) -> dict:
    """Generate a formatted report file. This is a long-running operation.

    Args:
        content: The report content to format.
        format: Output format ('pdf', 'docx').
    """
    # Simulate long-running processing
    await asyncio.sleep(2)

    return {
        "status": "completed",
        "format": format,
        "pages": max(1, len(content) // 500),
        "message": f"Report generated in {format} format.",
    }


# Wrap with LongRunningFunctionTool
pdf_report_tool = LongRunningFunctionTool(generate_pdf_report)
