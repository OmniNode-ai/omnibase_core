from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Trace Data Model.

Restrictive model for CLI execution trace data
with proper typing and validation.
"""


from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


class ModelTraceData(BaseModel):
    """Restrictive model for trace data.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    trace_id: UUID = Field(description="Unique trace identifier")
    span_id: UUID = Field(description="Span identifier")
    parent_span_id: UUID | None = Field(
        default=None, description="Parent span identifier"
    )
    start_time: datetime = Field(description="Start timestamp")
    end_time: datetime = Field(description="End timestamp")
    duration_ms: float = Field(description="Duration in milliseconds")
    tags: dict[str, str] = Field(default_factory=dict, description="Trace tags")
    logs: list[str] = Field(default_factory=list, description="Trace log entries")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e
