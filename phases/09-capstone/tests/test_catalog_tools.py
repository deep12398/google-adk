"""search_catalog 单元测试——不需要 LLM。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.catalog_tools import search_catalog


def _mock_ctx():
    ctx = MagicMock()
    ctx.state = {}
    return ctx


class TestSearchCatalog:

    def test_returns_dict(self):
        ctx = _mock_ctx()
        result = search_catalog("steel", ctx)
        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_finds_stainless_steel(self):
        ctx = _mock_ctx()
        result = search_catalog("stainless", ctx)
        assert result["total"] > 0
        assert all("stainless" in p["name"].lower() or "stainless" in p.get("category", "").lower()
                    for p in result["results"])

    def test_state_updated(self):
        ctx = _mock_ctx()
        search_catalog("steel", ctx)
        assert "catalog_results" in ctx.state
        assert ctx.state["search_count"] == 1
        assert ctx.state["last_query"] == "steel"

    def test_search_count_increments(self):
        ctx = _mock_ctx()
        search_catalog("steel", ctx)
        search_catalog("aluminum", ctx)
        assert ctx.state["search_count"] == 2

    def test_no_results_for_unknown(self):
        ctx = _mock_ctx()
        result = search_catalog("xyznonexistent", ctx)
        assert result["total"] == 0
        assert result["results"] == []

    def test_cascade_flag_on_few_results(self):
        ctx = _mock_ctx()
        result = search_catalog("titanium", ctx)
        # titanium 在 catalog 中很少，应触发级联
        if result["total"] < 5:
            assert ctx.state.get("catalog_exhausted") is True
            assert ctx.actions.transfer_to_agent == "supplier_search_agent"
