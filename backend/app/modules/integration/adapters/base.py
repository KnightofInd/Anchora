"""
Adapter Base Interface
----------------------
All external system connectors must implement this interface.
This abstraction is what keeps external integrations swappable
without touching any business logic.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Abstract base for all external system adapters."""

    @abstractmethod
    async def fetch_data(self, query: dict[str, Any]) -> dict[str, Any]:
        """Fetch data from the external system."""
        raise NotImplementedError

    @abstractmethod
    async def push_decision(self, decision_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Push a decision outcome to the external system."""
        raise NotImplementedError
