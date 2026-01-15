from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_type import EnumWorkflowType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

# Import extracted workflow data classes
from .model_conditional_workflow_data import ModelConditionalWorkflowData
from .model_loop_workflow_data import ModelLoopWorkflowData
from .model_parallel_workflow_data import ModelParallelWorkflowData
from .model_sequential_workflow_data import ModelSequentialWorkflowData
from .model_workflow_execution_context import ModelWorkflowExecutionContext


# Main workflow payload class (defined after all dependencies)
class ModelWorkflowPayload(BaseModel):
    """
    Strongly-typed workflow payload with discriminated unions.

    Replaces dict[str, Any] with discriminated workflow payload types.
    Implements Core protocols:
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
__all__ = ["ModelWorkflowPayload"]
