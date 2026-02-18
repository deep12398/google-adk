"""需求收集工具——品类推断 + 结构化需求。"""

import json
from pathlib import Path

from google.adk.tools import ToolContext

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(filename: str) -> list | dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def infer_category(product_description: str, tool_context: ToolContext) -> dict:
    """Infer product category from a description using the category taxonomy.

    Matches against category names and their aliases in categories.json.
    Sets product_category in state for downstream agents and skill loading.

    Args:
        product_description: The product description to classify.
    """
    categories = _load_json("categories.json")
    desc = product_description.lower()

    matches = []
    for cat_name, cat_info in categories.items():
        aliases = cat_info.get("aliases", [])
        if cat_name in desc or any(a.lower() in desc for a in aliases):
            matches.append({"category": cat_name, "parent": cat_info.get("parent", "")})

    if matches:
        tool_context.state["product_category"] = matches[0]["category"]

    return {
        "product_description": product_description,
        "inferred_categories": matches if matches else [{"category": "unknown", "parent": ""}],
    }


def collect_requirements(
    product_description: str,
    quantity: int = 0,
    quality_standard: str = "",
    budget_range: str = "",
    delivery_deadline: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Collect and structure sourcing requirements from user input.

    Args:
        product_description: What the user needs.
        quantity: Required quantity (0 if unknown).
        quality_standard: Required standard (e.g., ISO9001).
        budget_range: Budget range (e.g., "10000-20000 CNY").
        delivery_deadline: When needed (e.g., "2 weeks").
    """
    reqs = {
        "product": product_description,
        "quantity": quantity,
        "quality": quality_standard,
        "budget": budget_range,
        "deadline": delivery_deadline,
    }
    missing = [k for k, v in reqs.items() if not v]

    if tool_context:
        tool_context.state["requirements"] = reqs
        tool_context.state["temp:missing_fields"] = missing

    return {
        "requirements": reqs,
        "missing_fields": missing,
        "completeness": round((len(reqs) - len(missing)) / len(reqs), 2),
        "suggestion": f"Please also provide: {', '.join(missing)}" if missing else "All requirements collected!",
    }
