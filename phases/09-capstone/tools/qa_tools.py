"""Q&A 工具——产品对比 + 详情查询。

compare_products: 将多个产品拉出来做 side-by-side 对比
get_product_details: 查某个产品的详细信息 + 供应商信息
"""

import json
from pathlib import Path

from google.adk.tools import ToolContext

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(filename: str) -> list | dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def compare_products(product_ids: str, tool_context: ToolContext) -> dict:
    """Compare multiple products side by side.

    Args:
        product_ids: Comma-separated product IDs (e.g., "P001,P002,P003").
    """
    catalog = _load_json("catalog.json")
    ids = [pid.strip() for pid in product_ids.split(",")]
    products = [p for p in catalog if p["id"] in ids]

    if len(products) < 2:
        return {
            "error": f"Need at least 2 products to compare. Found {len(products)} for IDs: {ids}",
        }

    tool_context.state["temp:last_comparison"] = ids

    return {
        "products": products,
        "comparison_dimensions": [
            "price_range", "moq", "lead_time_days", "specs", "supplier_id",
        ],
        "count": len(products),
    }


def get_product_details(product_id: str, tool_context: ToolContext) -> dict:
    """Get detailed information about a specific product including supplier info.

    Args:
        product_id: The product ID (e.g., "P001").
    """
    catalog = _load_json("catalog.json")
    suppliers = _load_json("suppliers.json")

    product = next((p for p in catalog if p["id"] == product_id), None)
    if not product:
        return {"error": f"Product {product_id} not found."}

    # 补充供应商信息
    supplier = next(
        (s for s in suppliers if s["id"] == product.get("supplier_id")), None,
    )
    if supplier:
        product["supplier_details"] = supplier

    return product
