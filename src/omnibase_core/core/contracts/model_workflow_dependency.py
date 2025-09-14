"""
Model Workflow Dependency - ONEX Standards Compliant Workflow Dependency Specification.

Strongly-typed dependency model for workflow orchestration patterns that eliminates
legacy string-based dependency support and enforces architectural consistency.

ZERO TOLERANCE: No Any types, string fallbacks, or dict configs allowed.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.contracts.model_workflow_condition import ModelWorkflowCondition
from omnibase_core.core.contracts.model_workflow_dependency_config import (
    ModelWorkflowDependencyConfig,
)
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
    )

    version_constraint: ModelSemVer | None = Field(
        default=None,
        description="Version constraint for the dependent workflow",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the dependency",
    )

    # ONEX STRONG TYPES: UUID and ModelWorkflowCondition validation handled automatically by Pydantic

    @field_validator("condition", mode="before")
    @classmethod
    def validate_condition_structured_only(
        cls, v: ModelWorkflowCondition | dict | None
    ) -> ModelWorkflowCondition | None:
        """
        Validate condition is ModelWorkflowCondition instance only.

        STRONG TYPES ONLY: Accept ModelWorkflowCondition instances in Python code.
        YAML SERIALIZATION: Convert dict objects from YAML deserialization ONLY.
        NO FALLBACKS: Reject strings, Any types, or other legacy patterns.
        """
        if v is None:
            return v

        if isinstance(v, ModelWorkflowCondition):
            # STRONG TYPE: Already validated ModelWorkflowCondition instance
            return v
        elif isinstance(v, dict):
            # YAML SERIALIZATION ONLY: Convert dict from YAML to ModelWorkflowCondition
            try:
                return ModelWorkflowCondition.model_validate(v)
            except Exception as e:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Invalid condition structure: {str(e)}. Must contain: condition_type, field_name, operator, expected_value.",
                    context={
                        "context": {
                            "dict_keys": (
                                list(v.keys()) if isinstance(v, dict) else None
                            ),
                            "original_error": str(e),
                            "onex_principle": "Strong types with YAML dict conversion for serialization only",
                        }
                    },
                ) from e
        else:
            # STRONG TYPES ONLY: Reject all other types (strings, Any, etc.)
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"STRONG TYPES ONLY: condition must be ModelWorkflowCondition instance (or dict from YAML). Received {type(v).__name__}.",
                context={
                    "context": {
                        "received_type": str(type(v)),
                        "expected_type": "ModelWorkflowCondition",
                        "onex_principle": "STRONG TYPES ONLY - no strings, no Any types, no fallbacks",
                    }
                },
            )

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

    # STRONG TYPES ONLY: Use typed configuration model instead of dict
    _config_model: ModelWorkflowDependencyConfig = ModelWorkflowDependencyConfig(
        extra_fields_behavior="ignore",  # Allow extra fields from various input formats
        use_enum_values=False,  # Keep enum objects internally, serialize via alias
        validate_assignment=True,
        strip_whitespace=True,
    )

    # Pydantic model_config derived from typed configuration
    model_config = _config_model.to_pydantic_config_dict()
