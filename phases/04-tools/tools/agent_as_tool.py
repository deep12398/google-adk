from google.adk.tools import AgentTool

from agents.reviewer_agent import reviewer_agent

# Wrap the reviewer agent as a tool.
# Different from sub_agents:
#   - AgentTool = isolated invocation, parent keeps control
#   - sub_agents = control transfer, parent loses control during execution
review_tool = AgentTool(agent=reviewer_agent)
