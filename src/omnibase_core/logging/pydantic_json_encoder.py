from __future__ import annotations

"""
Custom JSON encoder for ONEX structured logging.

Handles Pydantic models, UUIDs, and log contexts.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


import json
from typing import Any
from unittest.mock import MagicMock, Mock
from uuid import UUID

from pydantic import BaseModel


class PydanticJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models, UUIDs, and log contexts."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, UUID):
            return str(obj)
        # Safety check: Don't call methods on Mock objects during serialization
        # Prevents deadlock in Mock._increment_mock_call() during gc
        if isinstance(obj, (Mock, MagicMock)):
            return repr(obj)
        # Handle ProtocolLogContext - use try/except to avoid other edge cases
        try:
            return obj.to_dict()
        except AttributeError:
            pass
        return super().default(obj)


# Export for use
__all__ = ["PydanticJSONEncoder"]
