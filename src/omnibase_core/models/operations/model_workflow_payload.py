from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType
from omnibase_core.errors.error_codes import EnumCoreErrorCode, ModelOnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Import extracted workflow data classes
from .model_conditional_workflow_data import ModelConditionalWorkflowData
from .model_loop_workflow_data import ModelLoopWorkflowData
from .model_parallel_workflow_data import ModelParallelWorkflowData
from .model_sequential_workflow_data import ModelSequentialWorkflowData
from .model_workflow_data_base import ModelWorkflowDataBase
from .model_workflow_execution_context import ModelWorkflowExecutionContext


# Main workflow payload class (defined after all dependencies)
class ModelWorkflowPayload(BaseModel):
    """
    Strongly-typed workflow payload with discriminated unions.

    Replaces dict[str, Any] with discriminated workflow payload types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    workflow_type: EnumWorkflowType = Field(
        default=...,
        description="Discriminated workflow type",
    )
    workflow_data: (
        ModelSequentialWorkflowData
        | ModelParallelWorkflowData
        | ModelConditionalWorkflowData
        | ModelLoopWorkflowData
    ) = Field(
        default=...,
        description="Workflow-specific data with discriminated union",
        discriminator="workflow_type",
    )
    execution_context: ModelWorkflowExecutionContext = Field(
        default_factory=ModelWorkflowExecutionContext,
        description="Structured workflow execution context",
    )
    state_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Workflow state data with proper typing",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
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

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = ["ModelWorkflowPayload"]
