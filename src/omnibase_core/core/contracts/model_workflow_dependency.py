"""
Model Workflow Dependency - ONEX Standards Compliant Workflow Dependency Specification.

Strongly-typed dependency model for workflow orchestration patterns that eliminates
legacy string-based dependency support and enforces architectural consistency.

ZERO TOLERANCE: No Any types or legacy string support allowed.
"""

from pydantic import BaseModel, Field, field_serializer, field_validator

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

    workflow_id: str = Field(
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

    @field_validator("workflow_id", mode="before")
    @classmethod
    def validate_workflow_id(cls, v: str | None) -> str:
        """
        Validate workflow ID follows proper naming conventions.

        Enforces lowercase, alphanumeric with hyphens format for consistency.
        """
        if v is None or not str(v) or not str(v).strip():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message="Workflow ID cannot be empty or whitespace-only",
                context={"workflow_id": v},
            )

        v = str(v)

        v = v.strip()

        # Length validation
        min_id_length = 2
        max_id_length = 64
        if len(v) < min_id_length:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Workflow ID too short: '{v}' (minimum {min_id_length} characters)",
                context={
                    "workflow_id": v,
                    "length": len(v),
                    "min_length": min_id_length,
                },
            )

        if len(v) > max_id_length:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Workflow ID too long: '{v}' (maximum {max_id_length} characters)",
                context={
                    "workflow_id": v,
                    "length": len(v),
                    "max_length": max_id_length,
                },
            )

        # Format validation: lowercase alphanumeric with hyphens, no consecutive hyphens
        import re

        pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
        if not re.match(pattern, v):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid workflow ID format: '{v}'",
                context={
                    "workflow_id": v,
                    "expected_format": "lowercase alphanumeric with hyphens (no consecutive hyphens, no leading/trailing hyphens)",
                    "pattern": pattern,
                },
            )

        return v

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
