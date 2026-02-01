"""
Custom JSON encoder for ONEX structured logging.

Handles Pydantic models, UUIDs, and log contexts.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, Mock
from uuid import UUID

from pydantic import BaseModel


class PydanticJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models, UUIDs, and log contexts."""

    def default(self, o: Any) -> Any:
        if isinstance(o, BaseModel):
            return o.model_dump()
        if isinstance(o, UUID):
            return str(o)
        # Safety check: Don't call methods on Mock objects during serialization
        # Prevents deadlock in Mock._increment_mock_call() during gc
        if isinstance(o, (Mock, MagicMock)):
            return repr(o)
        # Handle ProtocolLogContext - use try/except to avoid other edge cases
        try:
            return o.to_dict()
        except AttributeError:
            pass
        return super().default(o)


# Export for use
__all__ = ["PydanticJSONEncoder"]
