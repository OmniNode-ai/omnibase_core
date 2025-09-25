"""
Compensation Plan Model - ONEX Standards Compliant.

Strongly-typed compensation plan model that replaces dict[str, str | list[str]] patterns
with proper Pydantic validation and type safety for saga pattern workflows.

ZERO TOLERANCE: No Any types or dict patterns allowed.
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from omnibase_core.enums.enum_compensation_strategy import EnumCompensationStrategy
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_order import EnumExecutionOrder
from omnibase_core.exceptions.onex_error import OnexError


class ModelCompensationPlan(BaseModel):
    """
    Strongly-typed compensation plan for saga pattern workflows.

    Replaces dict[str, str | list[str]] patterns with proper Pydantic model
    providing runtime validation and type safety for compensation actions.

    ZERO TOLERANCE: No Any types or dict patterns allowed.
    """

    # Plan identification
    plan_id: UUID = Field(
        ...,
        description="Unique identifier for this compensation plan",
    )

    plan_name: str = Field(
        ...,
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
        default=300000,
        description="Total timeout for all compensation actions",
        ge=1000,
        le=3600000,  # Max 1 hour
    )

    action_timeout_ms: int = Field(
        default=30000,
        description="Timeout per individual compensation action",
        ge=1000,
        le=300000,  # Max 5 minutes
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
    depends_on_plans: list[str] = Field(
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
    def validate_plan_id(cls, v: Any) -> str:
        """Validate plan ID format."""
        if isinstance(v, UUID):
            v_str = str(v)
        elif isinstance(v, str):
            v_str = v.strip()
        else:
            from omnibase_core.models.common.model_error_context import (
                ModelErrorContext,
            )
            from omnibase_core.models.common.model_schema_value import ModelSchemaValue

            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Plan ID must be provided as a string or UUID",
                details=ModelErrorContext.with_context(
                    {"received_type": ModelSchemaValue.from_value(type(v).__name__)}
                ),
            )

        if not v_str:
            from omnibase_core.models.common.model_error_context import (
                ModelErrorContext,
            )
            from omnibase_core.models.common.model_schema_value import ModelSchemaValue

            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Plan ID cannot be empty",
                details=ModelErrorContext.with_context(
                    {"onex_principle": ModelSchemaValue.from_value("Strong types only")}
                ),
            )

        # Check for valid identifier format
        if not v_str.replace("_", "").replace("-", "").isalnum():
            from omnibase_core.models.common.model_error_context import (
                ModelErrorContext,
            )
            from omnibase_core.models.common.model_schema_value import ModelSchemaValue

            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid plan_id '{v_str}'. Must contain only alphanumeric characters, hyphens, and underscores.",
                details=ModelErrorContext.with_context(
                    {
                        "plan_id": ModelSchemaValue.from_value(v_str),
                        "onex_principle": ModelSchemaValue.from_value(
                            "Strong validation for identifiers"
                        ),
                    }
                ),
            )

        return v_str

    @field_validator(
        "rollback_actions",
        "cleanup_actions",
        "notification_actions",
        "recovery_actions",
    )
    @classmethod
    def validate_action_lists(cls, v: list[str]) -> list[str]:
        """Validate action identifier lists."""
        validated = []
        for action_id in v:
            action_id = action_id.strip()
            if not action_id:
                continue  # Skip empty entries

            if not action_id.replace("_", "").replace("-", "").isalnum():
                from omnibase_core.models.common.model_error_context import (
                    ModelErrorContext,
                )
                from omnibase_core.models.common.model_schema_value import (
                    ModelSchemaValue,
                )

                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid action_id '{action_id}'. Must contain only alphanumeric characters, hyphens, and underscores.",
                    details=ModelErrorContext.with_context(
                        {
                            "action_id": ModelSchemaValue.from_value(action_id),
                            "onex_principle": ModelSchemaValue.from_value(
                                "Strong validation for action identifiers"
                            ),
                        }
                    ),
                )

            validated.append(action_id)

        return validated

    @field_validator("depends_on_plans")
    @classmethod
    def validate_plan_dependencies(cls, v: list[str]) -> list[str]:
        """Validate plan dependency identifiers."""
        validated = []
        for plan_id in v:
            plan_id = plan_id.strip()
            if not plan_id:
                continue  # Skip empty entries

            if not plan_id.replace("_", "").replace("-", "").isalnum():
                from omnibase_core.models.common.model_error_context import (
                    ModelErrorContext,
                )
                from omnibase_core.models.common.model_schema_value import (
                    ModelSchemaValue,
                )

                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid dependency plan_id '{plan_id}'. Must contain only alphanumeric characters, hyphens, and underscores.",
                    details=ModelErrorContext.with_context(
                        {
                            "dependency_plan_id": ModelSchemaValue.from_value(plan_id),
                            "onex_principle": ModelSchemaValue.from_value(
                                "Strong validation for plan dependencies"
                            ),
                        }
                    ),
                )

            validated.append(plan_id)

        return validated

    model_config = ConfigDict(
        extra="forbid",  # Reject additional fields for strict typing
        validate_assignment=True,  # Validate on attribute assignment
        use_enum_values=True,  # Ensure proper enum serialization
    )

    def to_dict(self) -> dict[str, str | list[str] | bool | int]:
        """
        Convert to dictionary format for serialization.

        Returns:
            Dictionary representation with type information preserved
        """
        return self.model_dump(exclude_none=True, mode="json")

    @classmethod
    def from_dict(
        cls, data: dict[str, str | list[str] | bool | int]
    ) -> "ModelCompensationPlan":
        """
        Create from dictionary data with validation.

        Args:
            data: Dictionary containing compensation plan configuration

        Returns:
            Validated ModelCompensationPlan instance

        Raises:
            OnexError: If validation fails
        """
        try:
            return cls.model_validate(data)
        except OnexError:
            # Preserve existing domain error as-is
            raise
        except ValidationError as e:
            from omnibase_core.models.common.model_error_context import (
                ModelErrorContext,
            )
            from omnibase_core.models.common.model_schema_value import ModelSchemaValue

            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Compensation plan validation failed",
                details=ModelErrorContext.with_context(
                    {
                        "input_data": ModelSchemaValue.from_value(data),
                        "errors": ModelSchemaValue.from_value(e.errors()),
                    }
                ),
            ) from e
        except Exception as e:
            from omnibase_core.models.common.model_error_context import (
                ModelErrorContext,
            )
            from omnibase_core.models.common.model_schema_value import ModelSchemaValue

            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Compensation plan parsing failed: {e}",
                details=ModelErrorContext.with_context(
                    {"input_data": ModelSchemaValue.from_value(data)}
                ),
            ) from e
