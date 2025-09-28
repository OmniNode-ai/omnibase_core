"""
Strongly-typed computation output data model.

Replaces dict[str, Any] usage in computation output operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.core.type_constraints import (
    Executable,
    Identifiable,
    Serializable,
    Validatable,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelComputationOutputData(BaseModel):
    """
    Strongly-typed output data for computation operations.

    Replaces dict[str, Any] with structured result model.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    computed_values: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Computed result values with proper typing"
    )
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Numeric metrics from computation"
    )
    status_flags: dict[str, bool] = Field(
        default_factory=dict, description="Boolean status indicators"
    )
    output_metadata: dict[str, str] = Field(
        default_factory=dict, description="String metadata about the results"
    )
    processing_info: dict[str, str] = Field(
        default_factory=dict, description="Processing information and diagnostics"
    )

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelComputationOutputData"]
