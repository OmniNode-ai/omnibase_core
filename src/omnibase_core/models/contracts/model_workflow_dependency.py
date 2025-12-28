"""
Model Workflow Dependency Specification.

Strongly-typed dependency model for workflow orchestration patterns that eliminates
legacy string-based dependency support and enforces architectural consistency.

Strict typing is enforced: No Any types, string fallbacks, or dict[str, Any]configs allowed.
"""

# NO Any imports - Strict typing is enforced for Any types
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_dependency_type import EnumWorkflowDependencyType
from omnibase_core.models.contracts.model_workflow_condition import (
    ModelWorkflowCondition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflowDependency(BaseModel):
    """
    Strongly-typed workflow dependency specification.

    Provides structured workflow dependency definitions with proper type safety
    and validation for orchestration patterns. Eliminates legacy string-based
    dependency support completely.

    Strict typing is enforced: No Any types or string fallbacks allowed.
    """

    workflow_id: UUID = Field(
        default=...,
        description="Unique identifier of the workflow this dependency references",
    )

    dependent_workflow_id: UUID = Field(
        default=...,
        description="Unique identifier of the workflow that depends on the referenced workflow",
    )

    dependency_type: EnumWorkflowDependencyType = Field(
        default=...,
        description="Type of dependency relationship between workflows",
    )

    required: bool = Field(
        default=True,
        description="Whether this dependency is required for workflow execution",
    )

    condition: ModelWorkflowCondition | None = Field(
        default=None,
        description="Optional structured condition for conditional dependencies",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for dependency resolution in milliseconds",
        ge=1,
        le=TIMEOUT_LONG_MS,  # Max 5 minutes (TIMEOUT_LONG_MS)
    )

    version_constraint: ModelSemVer | None = Field(
        default=None,
        description="Version constraint for the dependent workflow",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the dependency",
    )

    @field_validator("workflow_id", mode="before")
    @classmethod
    def validate_workflow_id_uuid_only(cls, v: UUID) -> UUID:
        """
        Validate workflow_id is a proper UUID instance.

        Strict typing is enforced: Only accepts UUID objects - no string conversion.
        """
        if isinstance(v, UUID):
            return v
        # Strict typing is enforced: Reject all non-UUID types including strings
        raise ModelOnexError(
            message=f"workflow_id must be UUID instance, not {type(v).__name__}. No string conversion allowed.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    @field_validator("condition", mode="before")
    @classmethod
    def validate_condition_structured_only(
        cls,
        v: ModelWorkflowCondition | None,
    ) -> ModelWorkflowCondition | None:
        """
        Validate condition is ModelWorkflowCondition instance only.

        STRONG TYPES ONLY: Accept ModelWorkflowCondition instances ONLY.
        NO FALLBACKS: Reject dict[str, Any]s, strings, Any types, or other patterns.
        NO YAML CONVERSION: Use proper serialization/deserialization patterns instead.
        Strict typing is enforced: Parameter type matches implementation - no Any types allowed.
        """
        if v is None:
            return v

        if isinstance(v, ModelWorkflowCondition):
            # STRONG TYPE: Already validated ModelWorkflowCondition instance
            return v
        # STRONG TYPES ONLY: Reject all other types (dict[str, Any]s, strings, Any, etc.)
        raise ModelOnexError(
            message=f"STRONG TYPES ONLY: condition must be ModelWorkflowCondition instance. Received {type(v).__name__}.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    @model_validator(mode="after")
    def validate_no_circular_dependency(self) -> "ModelWorkflowDependency":
        """
        Prevent circular dependencies where a workflow depends on itself.

        CIRCULAR DEPENDENCY PREVENTION: Enforce that workflow_id ≠ dependent_workflow_id
        to prevent infinite loops in workflow execution.
        """
        if self.workflow_id == self.dependent_workflow_id:
            raise ModelOnexError(
                message=f"CIRCULAR DEPENDENCY DETECTED: Workflow {self.workflow_id} cannot depend on itself.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    def is_sequential(self) -> bool:
        """Check if dependency is sequential."""
        return self.dependency_type == EnumWorkflowDependencyType.SEQUENTIAL

    def is_parallel(self) -> bool:
        """Check if dependency allows parallel execution."""
        return self.dependency_type == EnumWorkflowDependencyType.PARALLEL

    def is_conditional(self) -> bool:
        """Check if dependency is conditional."""
        return self.dependency_type == EnumWorkflowDependencyType.CONDITIONAL

    def is_blocking(self) -> bool:
        """Check if dependency is blocking."""
        return self.dependency_type == EnumWorkflowDependencyType.BLOCKING

    def is_compensating(self) -> bool:
        """Check if dependency is compensating (saga pattern)."""
        return self.dependency_type == EnumWorkflowDependencyType.COMPENSATING

    # Clean Pydantic v2 configuration using ConfigDict
    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from various input formats
        use_enum_values=False,  # Keep enum objects internally, serialize via alias
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=False,  # Allow modification after creation
        populate_by_name=False,  # Use field names, not aliases
        json_schema_serialization_defaults_required=False,  # Don't require defaults in schema
    )
