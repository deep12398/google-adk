from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.tools import ToolContext


def exit_loop(tool_context: ToolContext, reason: str = "") -> dict:
    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
    return {"status": "exiting", "reason": reason}


critic_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="critic_agent",
    description="Finds issues in the current draft.",
    instruction=(
        "Review the draft and list the main issues or improvements. "
        "Draft:\n{draft}"
    ),
    output_key="critique",
)

refiner_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="refiner_agent",
    description="Refines the draft using critique; exits if no changes needed.",
    instruction=(
        "Improve the draft using the critique. If no changes are needed, "
        "call exit_loop with a short reason.\n\n"
        "Critique:\n{critique}\n\n"
        "Draft:\n{draft}"
    ),
    tools=[exit_loop],
    output_key="draft",
)

loop_agent = LoopAgent(
    name="refine_loop",
    description="Runs critic/refiner in a loop with a max of 3 iterations.",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=3,
)
