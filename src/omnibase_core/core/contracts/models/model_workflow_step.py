"""
Workflow Step Model - ONEX Standards Compliant.

Strongly-typed workflow step model that replaces dict[str, str | int | bool] patterns
with proper Pydantic validation and type safety.

ZERO TOLERANCE: No Any types or dict patterns allowed.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


class ModelWorkflowStep(BaseModel):
    """
    Strongly-typed workflow step definition.

    Replaces dict[str, str | int | bool] patterns with proper Pydantic model
    providing runtime validation and type safety for workflow execution.

    ZERO TOLERANCE: No Any types or dict patterns allowed.
    """

    step_id: str = Field(
        ...,
        description="Unique identifier for this workflow step",
        min_length=1,
        max_length=100,
    )

    step_name: str = Field(
        ...,
        description="Human-readable name for this step",
        min_length=1,
        max_length=200,
    )

    step_type: Literal[
        "compute",
        "effect",
        "reducer",
        "orchestrator",
        "conditional",
        "parallel",
        "custom",
    ] = Field(
        ...,
        description="Type of workflow step execution",
    )

    # Execution configuration
    timeout_ms: int = Field(
        default=30000,
        description="Step execution timeout in milliseconds",
        ge=100,
        le=300000,  # Max 5 minutes
    )

    retry_count: int = Field(
        default=3,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    # Conditional execution
    enabled: bool = Field(
        default=True,
        description="Whether this step is enabled for execution",
    )

    skip_on_failure: bool = Field(
        default=False,
        description="Whether to skip this step if previous steps failed",
    )

    # Error handling
    continue_on_error: bool = Field(
        default=False,
        description="Whether to continue workflow if this step fails",
    )

    error_action: Literal["stop", "continue", "retry", "compensate"] = Field(
        default="stop",
        description="Action to take when step fails",
    )

    # Performance requirements
    max_memory_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in megabytes",
        ge=1,
        le=32768,  # Max 32GB
    )

    max_cpu_percent: int | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
        ge=1,
        le=100,
    )

    # Priority and ordering
    priority: int = Field(
        default=100,
        description="Step execution priority (higher = more priority)",
        ge=1,
        le=1000,
    )

    order_index: int = Field(
        default=0,
        description="Order index for step execution sequence",
        ge=0,
    )

    # Dependencies
    depends_on: list[str] = Field(
        default_factory=list,
        description="List of step IDs this step depends on",
    )

    # Parallel execution
    parallel_group: str | None = Field(
        default=None,
        description="Group identifier for parallel execution",
        max_length=100,
    )

    max_parallel_instances: int = Field(
        default=1,
        description="Maximum parallel instances of this step",
        ge=1,
        le=100,
    )

    @field_validator("step_id")
    @classmethod
    def validate_step_id(cls, v: str) -> str:
        """Validate step ID format."""
        v = v.strip()
        if not v:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message="Step ID cannot be empty",
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Check for valid identifier format
        if not v.replace("_", "").replace("-", "").isalnum():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid step_id '{v}'. Must contain only alphanumeric characters, hyphens, and underscores.",
                context={
                    "context": {
                        "step_id": v,
                        "onex_principle": "Strong validation for identifiers",
                    }
                },
            )

        return v

    @field_validator("depends_on")
    @classmethod
    def validate_dependencies(cls, v: list[str]) -> list[str]:
        """Validate dependency step IDs."""
        validated = []
        for step_id in v:
            step_id = step_id.strip()
            if not step_id:
                continue  # Skip empty entries

            if not step_id.replace("_", "").replace("-", "").isalnum():
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Invalid dependency step_id '{step_id}'. Must contain only alphanumeric characters, hyphens, and underscores.",
                    context={
                        "context": {
                            "dependency_step_id": step_id,
                            "onex_principle": "Strong validation for dependencies",
                        }
                    },
                )

            validated.append(step_id)

        return validated

    class Config:
        """Pydantic configuration for ONEX compliance."""

        extra = "forbid"  # Reject additional fields for strict typing
        use_enum_values = True  # Convert enums to values
        validate_assignment = True

    def to_dict(self) -> dict[str, str | int | bool | list[str] | None]:
        """
        Convert to dictionary format for serialization.

        Returns:
            Dictionary representation with type information preserved
        """
        return self.model_dump(exclude_none=True, mode="python")

    @classmethod
    def from_dict(
        cls, data: dict[str, str | int | bool | list[str] | None]
    ) -> "ModelWorkflowStep":
        """
        Create from dictionary data with validation.

        Args:
            data: Dictionary containing step configuration

        Returns:
            Validated ModelWorkflowStep instance

        Raises:
            OnexError: If validation fails
        """
        try:
            return cls.model_validate(data)
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Workflow step validation failed: {e}",
                context={"context": {"input_data": data}},
            ) from e
