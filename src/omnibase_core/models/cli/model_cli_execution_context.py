"""
CLI Execution Context Model.

Represents custom execution context with proper validation.
Replaces dict[str, Any] for custom context with structured typing.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_context_source import EnumContextSource
from ...enums.enum_context_type import EnumContextType


class ModelCliExecutionContext(BaseModel):
    """
    Structured custom context for CLI execution.

    Replaces dict[str, Any] for custom_context to provide
    type safety and validation for execution context data.
    """

    # Context identification
    key: str = Field(..., description="Context key identifier")
    value: Any = Field(
        ...,
        description="Context value - validated against context_type discriminator",
    )

    # Context metadata
    context_type: EnumContextType = Field(..., description="Type of context data")
    is_persistent: bool = Field(default=False, description="Whether context persists")
    priority: int = Field(default=0, description="Context priority", ge=0, le=10)

    # Tracking
    created_at: datetime = Field(
        default_factory=datetime.now, description="Context creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Context last update time"
    )

    # Validation
    description: str = Field(default="", description="Context description")
    source: EnumContextSource = Field(
        default=EnumContextSource.USER, description="Context data source"
    )

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: Any, info) -> Any:
        """Validate that value matches its declared context type."""
        if hasattr(info, "data") and "context_type" in info.data:
            context_type = info.data["context_type"]

            # Basic type validation based on context type
            if context_type == EnumContextType.STRING and not isinstance(v, str):
                raise ValueError(
                    f"String context type must contain str data, got {type(v)}"
                )
            elif context_type == EnumContextType.NUMERIC and not isinstance(
                v, (int, float)
            ):
                raise ValueError(
                    f"Numeric context type must contain int/float data, got {type(v)}"
                )
            elif context_type == EnumContextType.BOOLEAN and not isinstance(v, bool):
                raise ValueError(
                    f"Boolean context type must contain bool data, got {type(v)}"
                )
            elif context_type == EnumContextType.DATETIME and not isinstance(
                v, datetime
            ):
                raise ValueError(
                    f"DateTime context type must contain datetime data, got {type(v)}"
                )
            elif context_type == EnumContextType.PATH and not isinstance(
                v, (Path, str)
            ):
                raise ValueError(
                    f"Path context type must contain Path/str data, got {type(v)}"
                )
            elif context_type == EnumContextType.UUID and not isinstance(
                v, (UUID, str)
            ):
                raise ValueError(
                    f"UUID context type must contain UUID/str data, got {type(v)}"
                )
            elif context_type == EnumContextType.LIST and not isinstance(v, list):
                raise ValueError(
                    f"List context type must contain list data, got {type(v)}"
                )

        return v

    def get_string_value(self) -> str:
        """Get value as string representation."""
        if isinstance(self.value, datetime):
            return self.value.isoformat()
        if isinstance(self.value, Path):
            return str(self.value)
        if isinstance(self.value, list):
            return ",".join(str(v) for v in self.value)
        return str(self.value)

    def get_typed_value(self) -> Any:
        """Get the properly typed value."""
        return self.value

    def is_datetime_value(self) -> bool:
        """Check if this is a datetime value."""
        return isinstance(self.value, datetime)

    def is_path_value(self) -> bool:
        """Check if this is a Path value."""
        return isinstance(self.value, Path)

    def is_uuid_value(self) -> bool:
        """Check if this is a UUID value."""
        return isinstance(self.value, UUID)

    def update_value(self, new_value: Any) -> None:
        """Update the context value and timestamp."""
        self.value = new_value
        self.updated_at = datetime.now()


# Export for use
__all__ = ["ModelCliExecutionContext"]
