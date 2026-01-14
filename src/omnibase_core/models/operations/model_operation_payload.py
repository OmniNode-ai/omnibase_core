"""
Strongly-typed operation payload structure.

Replaces dict[str, Any] usage in operation payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.operations.model_compute_operation_data import (
    ModelComputeOperationData,
)
from omnibase_core.models.operations.model_effect_operation_data import (
    ModelEffectOperationData,
)
from omnibase_core.models.operations.model_execution_metadata import (
    ModelExecutionMetadata,
)
from omnibase_core.models.operations.model_orchestrator_operation_data import (
    ModelOrchestratorOperationData,
)
from omnibase_core.models.operations.model_reducer_operation_data import (
    ModelReducerOperationData,
)
from omnibase_core.types.type_serializable_value import SerializedDict


# Main operation payload class (defined after all dependencies)
class ModelOperationPayload(BaseModel):
    """
    Strongly-typed operation payload with discriminated unions.

    Replaces dict[str, Any] with discriminated operation payload types.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique operation identifier (UUID format)",
    )
    operation_type: EnumNodeType = Field(
        default=...,
        description="Discriminated operation type (ONEX node type)",
    )
    operation_data: Annotated[
        ModelComputeOperationData
        | ModelEffectOperationData
        | ModelReducerOperationData
        | ModelOrchestratorOperationData,
        Field(discriminator="operation_type"),
    ] = Field(
        default=..., description="Operation-specific data with discriminated union"
    )
    execution_metadata: ModelExecutionMetadata | None = Field(
        default=None,
        description="Execution metadata for the operation",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
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
        raise ModelOnexError(
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        return True


# Export for use
__all__ = ["ModelOperationPayload"]
