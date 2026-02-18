"""Artifact 版本管理工具。

ADK Artifact 系统：
  - save_artifact(filename, Part, metadata) → 返回版本号（int）
  - load_artifact(filename, version) → 返回 Part（None 表示不存在）
  - list_artifacts() → 返回文件名列表

FileArtifactService 在文件系统中自动管理版本：
  root_dir/{app_name}/{user_id}/{session_id}/{filename}.{version}

每次 save 都创建新版本，版本号递增。load 不指定 version 时返回最新版本。
"""

from google.genai import types
from google.adk.tools import ToolContext


async def save_report(
    content: str, filename: str, tool_context: ToolContext
) -> dict:
    """保存报告为 artifact（自动版本管理）。

    Args:
        content: 报告内容。
        filename: 文件名，如 research_report.md。
    """
    part = types.Part.from_text(text=content)
    version = await tool_context.save_artifact(filename=filename, artifact=part)
    return {
        "status": "saved",
        "filename": filename,
        "version": version,
        "content_length": len(content),
        "note": f"Report saved as version {version}. Previous versions are preserved.",
    }


async def load_report(
    filename: str, tool_context: ToolContext, version: int = -1
) -> dict:
    """加载报告 artifact。

    Args:
        filename: 文件名。
        version: 版本号，-1 表示最新版本。
    """
    v = None if version == -1 else version
    part = await tool_context.load_artifact(filename=filename, version=v)
    if part is None:
        return {
            "status": "not_found",
            "filename": filename,
            "version": version,
        }
    return {
        "status": "loaded",
        "filename": filename,
        "version": version,
        "content": part.text if part.text else "(binary content)",
    }


async def list_reports(tool_context: ToolContext) -> dict:
    """列出当前 session 的所有 artifact 文件名。"""
    filenames = await tool_context.list_artifacts()
    return {
        "artifacts": filenames,
        "count": len(filenames),
    }
