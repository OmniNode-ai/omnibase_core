"""
Compensation Plan Model.

Strongly-typed compensation plan model that replaces dict[str, str | list[str]] patterns
with proper Pydantic validation and type safety for saga pattern workflows.

Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants import (
    TIMEOUT_DEFAULT_MS,
    TIMEOUT_LONG_MS,
    TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_compensation_strategy import EnumCompensationStrategy
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_order import EnumExecutionOrder
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelCompensationPlan(BaseModel):
    """
    Strongly-typed compensation plan for saga pattern workflows.

    Replaces dict[str, str | list[str]] patterns with proper Pydantic model
    providing runtime validation and type safety for compensation actions.

    Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
    """

    # Plan identification
    plan_id: UUID = Field(
        default=...,
        description="Unique identifier for this compensation plan",
    )

    plan_name: str = Field(
        default=...,
        description="Human-readable name for this compensation plan",
        min_length=1,
        max_length=200,
    )

    # Trigger conditions
    trigger_on_failure: bool = Field(
        default=True,
        description="Whether to trigger compensation on workflow failure",
    )

    trigger_on_timeout: bool = Field(
        default=True,
        description="Whether to trigger compensation on workflow timeout",
    )

    trigger_on_cancellation: bool = Field(
        default=True,
        description="Whether to trigger compensation on workflow cancellation",
    )

    # Compensation strategy
    compensation_strategy: EnumCompensationStrategy = Field(
        default=EnumCompensationStrategy.ROLLBACK,
        description="Overall compensation strategy",
    )

    execution_order: EnumExecutionOrder = Field(
        default=EnumExecutionOrder.REVERSE,
        description="Order to execute compensation actions",
    )

    # Timeout configuration
    total_timeout_ms: int = Field(
        default=TIMEOUT_LONG_MS,
        description="Total timeout for all compensation actions",
        ge=TIMEOUT_MIN_MS,
        le=3600000,  # Max 1 hour
    )

    action_timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Timeout per individual compensation action",
        ge=TIMEOUT_MIN_MS,
        le=TIMEOUT_LONG_MS,  # Max 5 minutes (TIMEOUT_LONG_MS)
    )

    # Compensation actions
    rollback_actions: list[str] = Field(
        default_factory=list,
        description="List of rollback action identifiers",
    )

    cleanup_actions: list[str] = Field(
        default_factory=list,
        description="List of cleanup action identifiers",
    )

    notification_actions: list[str] = Field(
        default_factory=list,
        description="List of notification action identifiers",
    )

    recovery_actions: list[str] = Field(
        default_factory=list,
        description="List of forward recovery action identifiers",
    )

    # Error handling
    continue_on_compensation_failure: bool = Field(
        default=False,
        description="Whether to continue if compensation actions fail",
    )

    max_compensation_retries: int = Field(
        default=3,
        description="Maximum retries for failed compensation actions",
        ge=0,
        le=10,
    )

    # Audit and logging
    audit_compensation: bool = Field(
        default=True,
        description="Whether to audit compensation action execution",
    )

    log_level: Literal["debug", "info", "warn", "error"] = Field(
        default="info",
        description="Logging level for compensation actions",
    )

    # Recovery policies
    partial_compensation_allowed: bool = Field(
        default=False,
        description="Whether partial compensation is acceptable",
    )

    idempotent_actions: bool = Field(
        default=True,
        description="Whether compensation actions are idempotent",
    )

    # Dependencies
    depends_on_plans: list[UUID] = Field(
        default_factory=list,
        description="List of other compensation plans this depends on",
    )

    # Priority and scheduling
    priority: int = Field(
        default=100,
        description="Compensation priority (higher = more priority)",
        ge=1,
        le=1000,
    )

    delay_before_execution_ms: int = Field(
        default=0,
        description="Delay before starting compensation execution",
        ge=0,
        le=60000,  # Max 1 minute delay
    )

    @field_validator("plan_id", mode="before")
    @classmethod
    def validate_plan_id(cls, v: UUID | str) -> UUID:
        """Validate plan ID format."""
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                raise ModelOnexError(
                    message="Plan ID cannot be empty",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "onex_principle": ModelSchemaValue.from_value(
                                "Strong types only",
                            ),
                        },
                    ),
                )

            # Try to parse as UUID
            try:
                return UUID(v_str)
            except ValueError:
                raise ModelOnexError(
                    message=f"Invalid plan_id '{v_str}'. Must be a valid UUID.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "plan_id": ModelSchemaValue.from_value(v_str),
                            "onex_principle": ModelSchemaValue.from_value(
                                "Strong validation for identifiers",
                            ),
                        },
                    ),
                )

    @field_validator(
        "rollback_actions",
        "cleanup_actions",
        "notification_actions",
        "recovery_actions",
    )
    @classmethod
    def validate_action_lists(cls, v: list[str]) -> list[str]:
        """Validate action identifier list[Any]s."""
        validated = []
        for action_id in v:
            action_id = action_id.strip()
            if not action_id:
                continue  # Skip empty entries

            if not action_id.replace("_", "").replace("-", "").isalnum():
                raise ModelOnexError(
                    message=f"Invalid action_id '{action_id}'. Must contain only alphanumeric characters, hyphens, and underscores.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "action_id": ModelSchemaValue.from_value(action_id),
                            "onex_principle": ModelSchemaValue.from_value(
                                "Strong validation for action identifiers",
                            ),
                        },
                    ),
                )

            validated.append(action_id)

        return validated

    @field_validator("depends_on_plans", mode="before")
    @classmethod
    def validate_plan_dependencies(cls, v: list[UUID | str]) -> list[UUID]:
        """Validate plan dependency identifiers."""
        validated = []
        for plan_id in v:
            if isinstance(plan_id, UUID):
                validated.append(plan_id)
            elif isinstance(plan_id, str):
                plan_id_str = plan_id.strip()
                if not plan_id_str:
                    continue  # Skip empty entries

                # Try to parse as UUID
                try:
                    validated.append(UUID(plan_id_str))
                except ValueError:
                    raise ModelOnexError(
                        message=f"Invalid dependency plan_id '{plan_id_str}'. Must be a valid UUID.",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        details=ModelErrorContext.with_context(
                            {
                                "dependency_plan_id": ModelSchemaValue.from_value(
                                    plan_id_str,
                                ),
                                "onex_principle": ModelSchemaValue.from_value(
                                    "Strong validation for plan dependencies",
                                ),
                            },
                        ),
                    )
            # Note: else clause removed as it's unreachable due to type annotation UUID | str

        return validated

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
