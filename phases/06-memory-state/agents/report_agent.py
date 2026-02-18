"""报告 Agent——使用 artifact_tools + memory_tools。

演示要点：
  1. search_memory 搜索历史 session 中的相关对话
  2. save_artifact 保存报告，自动版本管理
  3. load_artifact 加载历史版本
  4. list_artifacts 查看所有已保存的文件
  5. include_contents="none" 隔离对话历史（可选用于汇总场景）
"""

from google.adk.agents import LlmAgent

from tools.artifact_tools import save_report, load_report, list_reports
from tools.memory_tools import recall_past_research
from tools.event_tools import inspect_state_changes

report_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="report_agent",
    instruction=(
        "You are a report writer with memory and artifact capabilities.\n\n"
        "## Your Tools\n"
        "- **recall_past_research**: Search past session memories for relevant context\n"
        "- **save_report**: Save reports as versioned artifacts\n"
        "- **load_report**: Load a specific version of a report\n"
        "- **list_reports**: List all saved artifacts\n"
        "- **inspect_state_changes**: View the event sourcing history\n\n"
        "## Workflow\n"
        "1. First, use recall_past_research to find any relevant prior work.\n"
        "2. Write a comprehensive report based on available context.\n"
        "3. Save the report using save_report with a descriptive filename.\n"
        "4. If asked to update, load the previous version, modify, and save again.\n"
        "5. The versioning system preserves all previous versions automatically.\n"
    ),
    tools=[
        recall_past_research,
        save_report,
        load_report,
        list_reports,
        inspect_state_changes,
    ],
    output_key="report_output",
)
