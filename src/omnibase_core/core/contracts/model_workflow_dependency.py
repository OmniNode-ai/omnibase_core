"""
Model Workflow Dependency - ONEX Standards Compliant Workflow Dependency Specification.

Strongly-typed dependency model for workflow orchestration patterns that eliminates
legacy string-based dependency support and enforces architectural consistency.

ZERO TOLERANCE: No Any types or legacy string support allowed.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

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

    dependency_type: EnumWorkflowDependencyType = Field(
        ...,
        description="Type of dependency relationship between workflows",
    )

    required: bool = Field(
        default=True,
        description="Whether this dependency is required for workflow execution",
    )

    condition: str | None = Field(
        default=None,
        description="Optional condition for conditional dependencies",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for dependency resolution in milliseconds",
        ge=1,
    )

    version_constraint: ModelSemVer | None = Field(
        default=None,
        description="Version constraint for the dependent workflow",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the dependency",
    )

    # ONEX STRONG TYPES: UUID validation handled automatically by Pydantic

    @field_validator("condition", mode="before")
    @classmethod
    def validate_condition_format(cls, v: str | None) -> str | None:
        """Validate condition format when provided."""
        if v is None:
            return v

        if not isinstance(v, str):
            v = str(v)

        v = v.strip()
        if not v:
            return None

        # Basic validation - ensure it's not empty after stripping
        min_condition_length = 3
        if len(v) < min_condition_length:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Condition too short: '{v}' (minimum {min_condition_length} characters)",
                context={
                    "condition": v,
                    "length": len(v),
                    "min_length": min_condition_length,
                },
            )

        return v

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

    model_config = {
        "extra": "ignore",  # Allow extra fields from various input formats
        "use_enum_values": False,  # Keep enum objects internally, serialize via alias
        "validate_assignment": True,
        "str_strip_whitespace": True,
    }
