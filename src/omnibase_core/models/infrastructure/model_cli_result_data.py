from __future__ import annotations

import uuid

from pydantic import Field

"""
CLI result data model.

CLI result data model with typed fields for command execution results.
Follows ONEX one-model-per-file naming conventions.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties

from .model_cli_value import ModelCliValue


class ModelCliResultData(BaseModel):
    """CLI result data model with typed fields.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    success: bool = Field(description="Whether execution was successful")
    execution_id: UUID = Field(description="Execution identifier")
    output_data: ModelCliValue | None = Field(
        default=None,
        description="Output data if successful",
    )
    error_message: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Error message if failed",
    )
    # Entity reference with UUID
    tool_id: UUID | None = Field(description="Unique identifier of the tool")
    tool_display_name: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Human-readable tool name if available",
    )
    execution_time_ms: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(0),
        description="Execution time in milliseconds",
    )
    status_code: int = Field(description="Status code")
    warnings: list[str] = Field(description="Warning messages")
    metadata: ModelCustomProperties = Field(description="Execution metadata")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelCliResultData"]
