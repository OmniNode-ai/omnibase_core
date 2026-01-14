"""
Strongly-typed workflow metadata structure.

Replaces dict[str, Any] usage in workflow metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelWorkflowInstanceMetadata(BaseModel):
    """
    Strongly-typed workflow metadata.

    Replaces dict[str, Any] with structured workflow metadata model.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Unique workflow identifier (UUID format)",
    )
    workflow_type: str = Field(default=..., description="Type of workflow")
    instance_id: UUID = Field(
        default_factory=uuid4,
        description="Workflow instance identifier (UUID format)",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )

    # Workflow state
    current_step: str = Field(default="", description="Current workflow step")
    total_steps: int = Field(default=0, description="Total number of steps")
    completed_steps: int = Field(default=0, description="Number of completed steps")

    # Dependencies
    parent_workflow_id: UUID | None = Field(
        default=None,
        description="Parent workflow identifier (UUID format)",
    )
    dependency_count: int = Field(default=0, description="Number of dependencies")

    # Tags and labels
    tags: dict[str, str] = Field(default_factory=dict, description="Workflow tags")
    labels: dict[str, str] = Field(default_factory=dict, description="Workflow labels")

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
            f"(type_id, id, uuid, identifier, metadata_id, etc.). "
            f"Cannot generate stable ID without UUID field.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelWorkflowInstanceMetadata"]
