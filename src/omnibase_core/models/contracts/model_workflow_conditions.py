"""
Workflow Conditions Model.

Strongly-typed workflow conditions model that replaces dict[str, str | bool | int] patterns
with proper Pydantic validation and type safety.

Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelWorkflowConditions(BaseModel):
    """
    Strongly-typed workflow conditions definition.

    Replaces dict[str, str | bool | int] patterns with proper Pydantic model
    providing runtime validation and type safety for conditional workflow execution.

    Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
    """

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking workflow conditions across operations",
    )

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
        max_length=MAX_IDENTIFIER_LENGTH,
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
        default=TIMEOUT_LONG_MS,
        description="Timeout for dependency completion in milliseconds",
        ge=1000,
        le=3600000,  # Max 1 hour
    )

    # State conditions
    required_state: str | None = Field(
        default=None,
        description="Required workflow state for execution",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    forbidden_state: str | None = Field(
        default=None,
        description="Forbidden workflow state that prevents execution",
        max_length=MAX_IDENTIFIER_LENGTH,
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
        max_length=MAX_IDENTIFIER_LENGTH,
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
                raise ModelOnexError(
                    message=f"Invalid schedule expression '{v}'. Must have 5 or 6 parts (minute hour day month weekday [second]).",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
                raise ModelOnexError(
                    message=f"Invalid environment '{env}'. Must be one of: {', '.join(valid_environments)}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

            validated.append(env)

        return validated

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
