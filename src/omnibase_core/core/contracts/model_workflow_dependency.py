"""
Model Workflow Dependency - ONEX Standards Compliant Workflow Dependency Specification.

Strongly-typed dependency model for workflow orchestration patterns that eliminates
legacy string-based dependency support and enforces architectural consistency.

ZERO TOLERANCE: No Any types or legacy string support allowed.
"""

from pydantic import BaseModel, Field, field_validator

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
        min_length=1,
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

    @field_validator("workflow_id")
    @classmethod
    def validate_workflow_id(cls, v: str) -> str:
        """Validate workflow ID follows proper naming conventions."""
        if not v or not v.strip():
            msg = "Workflow ID cannot be empty or whitespace-only"
            raise ValueError(msg)

        v = v.strip()

        # Basic validation - ensure it's a proper identifier
        min_id_length = 2
        if len(v) < min_id_length:
            msg = f"Workflow ID too short: {v}"
            raise ValueError(msg)

        return v

    @field_validator("condition")
    @classmethod
    def validate_condition_format(cls, v: str | None) -> str | None:
        """Validate condition format when provided."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Basic validation - ensure it's not empty after stripping
        min_condition_length = 3
        if len(v) < min_condition_length:
            msg = f"Condition too short: {v}"
            raise ValueError(msg)

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

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary representation."""
        result_dict = {
            "workflow_id": self.workflow_id,
            "dependency_type": self.dependency_type.value,
        }

        # Add optional fields using dict.update() to avoid subscript access
        optional_data = {}

        if not self.required:
            optional_data.update(required=self.required)

        if self.condition:
            optional_data.update(condition=self.condition)

        if self.timeout_ms:
            optional_data.update(timeout_ms=self.timeout_ms)

        if self.version_constraint:
            version_data = (
                self.version_constraint.model_dump()
                if isinstance(self.version_constraint, ModelSemVer)
                else self.version_constraint
            )
            optional_data.update(version_constraint=version_data)

        if self.description:
            optional_data.update(description=self.description)

        result_dict.update(optional_data)
        return result_dict

    model_config = {
        "extra": "ignore",  # Allow extra fields from various input formats
        "use_enum_values": False,  # Keep enum objects, don't convert to strings
        "validate_assignment": True,
        "str_strip_whitespace": True,
    }
