"""Sourcing Orchestrator——根 Agent。

Step 8 版本：GenerateContentConfig(temperature=0.1) 确定性路由。
"""

from google.genai import types

from google.adk.agents.llm_agent import LlmAgent

from agents.catalog_search_agent import catalog_search_agent
from agents.chitchat_agent import chitchat_agent
from agents.intent_agent import intent_agent
from agents.qa_agent import qa_agent
from agents.quote_agent import quote_agent
from agents.requirements_agent import requirements_agent
from agents.supplier_search_agent import supplier_search_agent
from agents.web_search_agent import web_search_agent
from callbacks.sourcing_callbacks import (
    after_agent_cb,
    after_model_cb,
    before_agent_cb,
    before_model_cb,
    on_model_error_cb,
)
from prompts.templates import FULL_ROUTING_PROMPT
from tools.memory_tools import recall_search_history, save_document
from tools.preference_tools import get_preference, list_preferences, set_preference

sourcing_orchestrator = LlmAgent(
    model="gemini-2.0-flash",
    name="sourcing_orchestrator",
    description="Full sourcing assistant with 8 specialized sub-agents.",
    instruction=FULL_ROUTING_PROMPT,
    tools=[
        recall_search_history, save_document,
        set_preference, get_preference, list_preferences,
    ],
    sub_agents=[
        intent_agent, requirements_agent,
        catalog_search_agent, supplier_search_agent,
        web_search_agent, qa_agent, quote_agent,
        chitchat_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    before_agent_callback=before_agent_cb,
    after_agent_callback=after_agent_cb,
    before_model_callback=before_model_cb,
    after_model_callback=after_model_cb,
    on_model_error_callback=on_model_error_cb,
)
