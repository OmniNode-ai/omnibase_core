"""
Model Workflow Dependency - ONEX Standards Compliant Workflow Dependency Specification.

Strongly-typed dependency model for workflow orchestration patterns that eliminates
legacy string-based dependency support and enforces architectural consistency.

ZERO TOLERANCE: No Any types, string fallbacks, or dict configs allowed.
"""

# NO Any imports - ZERO TOLERANCE for Any types
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.core.contracts.model_workflow_condition import ModelWorkflowCondition
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_workflow_dependency_type import EnumWorkflowDependencyType
from omnibase_core.models.core.model_semver import ModelSemVer


class ModelWorkflowDependency(BaseModel):
    """
    Strongly-typed workflow dependency specification.

    Provides structured workflow dependency definitions with proper type safety
    and validation for orchestration patterns. Eliminates legacy string-based
    dependency support completely.

    ZERO TOLERANCE: No Any types or string fallbacks allowed.
    """

    workflow_id: UUID = Field(
        ...,
        description="Unique identifier of the workflow this dependency references",
    )

    dependent_workflow_id: UUID = Field(
        ...,
        description="Unique identifier of the workflow that depends on the referenced workflow",
    )

    dependency_type: EnumWorkflowDependencyType = Field(
        ...,
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
        le=300000,  # Max 5 minutes to prevent configuration errors
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

        ZERO TOLERANCE: Only accepts UUID objects - no string conversion.
        """
        if isinstance(v, UUID):
            return v
        else:
            # ZERO TOLERANCE: Reject all non-UUID types including strings
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"workflow_id must be UUID instance, not {type(v).__name__}. No string conversion allowed.",
                context={
                    "received_type": str(type(v)),
                    "expected_type": "UUID",
                    "zero_tolerance_policy": "Only UUID instances accepted",
                },
            )

    @field_validator("condition", mode="before")
    @classmethod
    def validate_condition_structured_only(
        cls, v: ModelWorkflowCondition | None
    ) -> ModelWorkflowCondition | None:
        """
        Validate condition is ModelWorkflowCondition instance only.

        STRONG TYPES ONLY: Accept ModelWorkflowCondition instances ONLY.
        NO FALLBACKS: Reject dicts, strings, Any types, or other patterns.
        NO YAML CONVERSION: Use proper serialization/deserialization patterns instead.
        ZERO TOLERANCE: Parameter type matches implementation - no Any types allowed.
        """
        if v is None:
            return v

        if isinstance(v, ModelWorkflowCondition):
            # STRONG TYPE: Already validated ModelWorkflowCondition instance
            return v
        else:
            # STRONG TYPES ONLY: Reject all other types (dicts, strings, Any, etc.)
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"STRONG TYPES ONLY: condition must be ModelWorkflowCondition instance. Received {type(v).__name__}.",
                context={
                    "received_type": str(type(v)),
                    "received_value": str(v)[:100],  # First 100 chars for debugging
                    "expected_type": "ModelWorkflowCondition",
                    "onex_principle": "STRONG TYPES ONLY - no dicts, no strings, no Any types, no fallbacks",
                    "correct_usage": "ModelWorkflowCondition(condition_type=EnumConditionType.WORKFLOW_STATE, field_name='status', operator=EnumConditionOperator.EQUALS, expected_value='completed')",
                    "migration_guide": "See docs/migration/contract-dependency-refactor.md for conversion examples",
                },
            )

    @model_validator(mode="after")
    def validate_no_circular_dependency(self) -> "ModelWorkflowDependency":
        """
        Prevent circular dependencies where a workflow depends on itself.

        CIRCULAR DEPENDENCY PREVENTION: Enforce that workflow_id ≠ dependent_workflow_id
        to prevent infinite loops in workflow execution.
        """
        if self.workflow_id == self.dependent_workflow_id:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"CIRCULAR DEPENDENCY DETECTED: Workflow {self.workflow_id} cannot depend on itself.",
                context={
                    "workflow_id": str(self.workflow_id),
                    "dependent_workflow_id": str(self.dependent_workflow_id),
                    "onex_principle": "Circular dependency prevention for workflow orchestration",
                    "suggested_fix": "Ensure workflow_id and dependent_workflow_id are different UUIDs",
                    "prevention_type": "circular_dependency",
                },
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
        use_list=True,  # Use list type for array-like fields
        json_schema_serialization_defaults_required=False,  # Don't require defaults in schema
    )
