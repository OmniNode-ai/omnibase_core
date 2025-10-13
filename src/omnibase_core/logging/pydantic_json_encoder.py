from __future__ import annotations

import uuid

"""
Custom JSON encoder for ONEX structured logging.

Handles Pydantic models, UUIDs, and log contexts.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class PydanticJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models, UUIDs, and log contexts."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "to_dict"):  # Handle ProtocolLogContext
            return obj.to_dict()
        return super().default(obj)


# Export for use
__all__ = ["PydanticJSONEncoder"]
