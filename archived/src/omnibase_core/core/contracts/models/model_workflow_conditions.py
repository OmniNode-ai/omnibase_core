"""
Workflow Conditions Model - ONEX Standards Compliant.

Strongly-typed workflow conditions model that replaces dict[str, str | bool | int] patterns
with proper Pydantic validation and type safety.

ZERO TOLERANCE: No Any types or dict patterns allowed.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


class ModelWorkflowConditions(BaseModel):
    """
    Strongly-typed workflow conditions definition.

    Replaces dict[str, str | bool | int] patterns with proper Pydantic model
    providing runtime validation and type safety for conditional workflow execution.

    ZERO TOLERANCE: No Any types or dict patterns allowed.
    """

    # Execution conditions
    enable_condition: str | None = Field(
        default=None,
        description="Condition expression to enable workflow execution",
        max_length=500,
    )

    skip_condition: str | None = Field(
        default=None,
        description="Condition expression to skip workflow execution",
        max_length=500,
    )

    # Resource-based conditions
    min_memory_mb: int | None = Field(
        default=None,
        description="Minimum available memory required in megabytes",
        ge=1,
        le=32768,
    )

    min_cpu_percent: int | None = Field(
        default=None,
        description="Minimum available CPU percentage required",
        ge=1,
        le=100,
    )

    min_disk_space_mb: int | None = Field(
        default=None,
        description="Minimum available disk space in megabytes",
        ge=1,
    )

    # Time-based conditions
    schedule_expression: str | None = Field(
        default=None,
        description="Cron-like schedule expression for time-based execution",
        max_length=100,
    )

    timeout_before_ms: int | None = Field(
        default=None,
        description="Timeout before which workflow must complete",
        ge=1000,
        le=86400000,  # Max 24 hours
    )

    # Dependency conditions
    require_all_dependencies: bool = Field(
        default=True,
        description="Whether all dependencies must be satisfied",
    )

    wait_for_dependencies: bool = Field(
        default=True,
        description="Whether to wait for dependencies to complete",
    )

    dependency_timeout_ms: int = Field(
        default=300000,
        description="Timeout for dependency completion in milliseconds",
        ge=1000,
        le=3600000,  # Max 1 hour
    )

    # State conditions
    required_state: str | None = Field(
        default=None,
        description="Required workflow state for execution",
        max_length=100,
    )

    forbidden_state: str | None = Field(
        default=None,
        description="Forbidden workflow state that prevents execution",
        max_length=100,
    )

    # Environment conditions
    required_environment: str | None = Field(
        default=None,
        description="Required environment for execution (dev, staging, prod)",
        max_length=50,
    )

    allowed_environments: list[str] = Field(
        default_factory=list,
        description="List of allowed execution environments",
    )

    forbidden_environments: list[str] = Field(
        default_factory=list,
        description="List of forbidden execution environments",
    )

    # User/role conditions
    required_role: str | None = Field(
        default=None,
        description="Required user role for execution",
        max_length=100,
    )

    required_permissions: list[str] = Field(
        default_factory=list,
        description="List of required permissions",
    )

    # Feature flags
    required_feature_flags: list[str] = Field(
        default_factory=list,
        description="List of required feature flags to be enabled",
    )

    forbidden_feature_flags: list[str] = Field(
        default_factory=list,
        description="List of feature flags that must be disabled",
    )

    # Circuit breaker conditions
    max_failure_rate_percent: int | None = Field(
        default=None,
        description="Maximum failure rate percentage before circuit opens",
        ge=0,
        le=100,
    )

    max_consecutive_failures: int | None = Field(
        default=None,
        description="Maximum consecutive failures before circuit opens",
        ge=1,
        le=100,
    )

    @field_validator("schedule_expression")
    @classmethod
    def validate_schedule_expression(cls, v: str | None) -> str | None:
        """Validate cron-like schedule expression format."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Basic validation - should have 5 or 6 parts (seconds optional)
            parts = v.split()
            if len(parts) not in [5, 6]:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Invalid schedule expression '{v}'. Must have 5 or 6 parts (minute hour day month weekday [second]).",
                    context={
                        "context": {
                            "schedule_expression": v,
                            "onex_principle": "Strong validation for time-based conditions",
                        }
                    },
                )

        return v

    @field_validator("allowed_environments", "forbidden_environments")
    @classmethod
    def validate_environments(cls, v: list[str]) -> list[str]:
        """Validate environment names."""
        validated = []
        valid_environments = {"dev", "test", "staging", "prod", "production", "local"}

        for env in v:
            env = env.strip().lower()
            if not env:
                continue

            if env not in valid_environments:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Invalid environment '{env}'. Must be one of: {', '.join(valid_environments)}",
                    context={
                        "context": {
                            "environment": env,
                            "valid_environments": list(valid_environments),
                            "onex_principle": "Strong validation for environment conditions",
                        }
                    },
                )

            validated.append(env)

        return validated

    class Config:
        """Pydantic configuration for ONEX compliance."""

        extra = "forbid"  # Reject additional fields for strict typing
        validate_assignment = True

    def to_dict(self) -> dict[str, str | bool | int | list[str] | None]:
        """
        Convert to dictionary format for serialization.

        Returns:
            Dictionary representation with type information preserved
        """
        return self.model_dump(exclude_none=True, mode="python")

    @classmethod
    def from_dict(
        cls, data: dict[str, str | bool | int | list[str] | None]
    ) -> "ModelWorkflowConditions":
        """
        Create from dictionary data with validation.

        Args:
            data: Dictionary containing conditions configuration

        Returns:
            Validated ModelWorkflowConditions instance

        Raises:
            OnexError: If validation fails
        """
        try:
            return cls.model_validate(data)
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Workflow conditions validation failed: {e}",
                context={"context": {"input_data": data}},
            ) from e
