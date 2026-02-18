"""报价工具——生成结构化报价单。

读取 state 中的 requirements（来自 requirements_agent），
结合用户指定的产品和数量，输出标准报价单。
"""

from datetime import datetime, timezone

from google.adk.tools import ToolContext


def generate_quote(
    product_id: str,
    quantity: int,
    delivery_deadline: str = "",
    special_requirements: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Generate a price quote for a specific product.

    Reads requirements from state if available.

    Args:
        product_id: The product to quote.
        quantity: Number of units / tons requested.
        delivery_deadline: Requested delivery date (e.g., "2 weeks").
        special_requirements: Any special requirements (e.g., "mirror finish").
    """
    # 从 state 读取已收集的需求
    requirements = {}
    if tool_context:
        requirements = tool_context.state.get("requirements", {})

    quote = {
        "quote_id": f"Q-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "product_id": product_id,
        "quantity": quantity,
        "unit": requirements.get("unit", "tons"),
        "delivery_deadline": delivery_deadline or requirements.get("deadline", "TBD"),
        "special_requirements": special_requirements or requirements.get("quality", ""),
        "estimated_unit_price": "3,000 CNY/ton",
        "estimated_total": f"{3000 * max(quantity, 1):,} CNY",
        "validity": "7 days",
        "payment_terms": "30% deposit, 70% before shipment",
        "status": "draft",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if tool_context:
        tool_context.state["last_quote"] = quote

    return quote
