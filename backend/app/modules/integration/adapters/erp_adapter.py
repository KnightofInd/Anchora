"""
ERP Mock Adapter
----------------
Demo-scale mock of an ERP system integration.
In production, replace fetch_data / push_decision with real ERP API calls.
"""

from typing import Any
from app.modules.integration.adapters.base import BaseAdapter


class ERPAdapter(BaseAdapter):
    """Mock ERP adapter for university demo scope."""

    async def fetch_data(self, query: dict[str, Any]) -> dict[str, Any]:
        # TODO Phase 6: Replace with real ERP HTTP call
        return {
            "source": "erp_mock",
            "data": {"budget_remaining": 500000, "department": "operations"},
        }

    async def push_decision(self, decision_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        # TODO Phase 6: Push approved decision to ERP workflow
        return {"status": "pushed", "decision_id": decision_id, "erp_reference": "ERP-MOCK-001"}
