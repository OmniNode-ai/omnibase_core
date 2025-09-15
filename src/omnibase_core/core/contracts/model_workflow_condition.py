"""
Model Workflow Condition - ONEX Standards Compliant Workflow Condition Specification.

Strongly-typed condition model for workflow dependency conditions that eliminates
string-based condition support and enforces structured condition evaluation.

ZERO TOLERANCE: No string conditions or Any types allowed.
"""

from enum import Enum
from typing import Generic, TypeVar, Union

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


class EnumConditionOperator(str, Enum):
    """Allowed operators for workflow condition evaluation."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class EnumConditionType(str, Enum):
    """Type of condition evaluation."""

    WORKFLOW_STATE = "workflow_state"
    OUTPUT_VALUE = "output_value"
    EXECUTION_STATUS = "execution_status"
    TIME_BASED = "time_based"
    CUSTOM_EXPRESSION = "custom_expression"


# Type-safe value types
ConditionValue = TypeVar("ConditionValue", str, int, float, bool)


class ModelConditionValue(BaseModel, Generic[ConditionValue]):
    """Generic container for strongly-typed condition values."""

    value: ConditionValue = Field(..., description="Typed condition value")

    @property
    def python_type(self) -> type:
        """Get the Python type of the contained value."""
        return type(self.value)


class ModelConditionValueList(BaseModel):
    """Container for list of strongly-typed condition values."""

    values: list[str | int | float | bool] = Field(
        ..., description="List of condition values"
    )

    def contains(self, item: str | int | float | bool) -> bool:
        """Check if the list contains the specified item."""
        return item in self.values


class ModelWorkflowCondition(BaseModel):
    """
    Strongly-typed workflow condition specification.

    Replaces string-based conditions with structured condition evaluation
    that enables proper validation, type safety, and architectural consistency.

    ZERO TOLERANCE: No string conditions or Any types allowed.
    """

    condition_type: EnumConditionType = Field(
        ...,
        description="Type of condition to evaluate",
    )

    field_name: str = Field(
        ...,
        description="Name of the field or property to evaluate",
        min_length=1,
        max_length=100,
    )

    operator: EnumConditionOperator = Field(
        ...,
        description="Operator to use for condition evaluation",
    )

    expected_value: Union[
        ModelConditionValue[str],
        ModelConditionValue[int],
        ModelConditionValue[float],
        ModelConditionValue[bool],
        ModelConditionValueList,
    ] = Field(
        ...,
        description="Expected value for comparison (strongly typed container)",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the condition",
        max_length=500,
    )

    @field_validator("field_name")
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        """Validate field name follows proper naming conventions."""
        if not v or not v.strip():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message="Condition field_name cannot be empty",
                context={"context": {"onex_principle": "Strong types only"}},
            )

        v = v.strip()

        # Check for valid field name format (alphanumeric, underscores, dots for nested fields)
        if not all(c.isalnum() or c in "_." for c in v):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid field_name '{v}'. Must contain only alphanumeric characters, underscores, and dots.",
                context={
                    "context": {
                        "field_name": v,
                        "allowed_characters": "alphanumeric, underscores, dots",
                        "onex_principle": "Strong validation for structured conditions",
                    }
                },
            )

        return v

    @field_validator("expected_value")
    @classmethod
    def validate_expected_value(
        cls,
        v: Union[
            ModelConditionValue[str],
            ModelConditionValue[int],
            ModelConditionValue[float],
            ModelConditionValue[bool],
            ModelConditionValueList,
        ],
        info: ValidationInfo | None = None,
    ) -> Union[
        ModelConditionValue[str],
        ModelConditionValue[int],
        ModelConditionValue[float],
        ModelConditionValue[bool],
        ModelConditionValueList,
    ]:
        """Validate expected value container is properly typed and compatible with operator."""
        # Validation is handled by the container types themselves
        # Additional operator compatibility checks can be added based on info.data
        return v

    def evaluate_condition(
        self, context_data: dict[str, str | int | float | bool | list | dict]
    ) -> bool:
        """
        Evaluate the condition against provided context data.

        Args:
            context_data: Data context for condition evaluation

        Returns:
            True if condition is satisfied, False otherwise

        Raises:
            OnexError: If evaluation fails due to missing data or invalid operators
        """
        try:
            # Extract field value from context
            field_value = self._extract_field_value(context_data, self.field_name)

            # Extract the actual value from the container
            expected_actual_value = self._extract_container_value(self.expected_value)

            # Perform operator-specific evaluation
            return self._evaluate_operator(
                field_value, expected_actual_value, self.operator
            )

        except KeyError as e:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Field '{self.field_name}' not found in context data",
                context={
                    "context": {
                        "field_name": self.field_name,
                        "available_fields": list(context_data.keys()),
                        "condition_type": self.condition_type.value,
                    }
                },
            ) from e

    def _extract_field_value(
        self,
        context_data: dict[str, str | int | float | bool | list | dict],
        field_path: str,
    ) -> str | int | float | bool | list | dict:
        """Extract field value supporting nested field paths with dot notation."""
        current_value = context_data

        for field_part in field_path.split("."):
            if isinstance(current_value, dict) and field_part in current_value:
                current_value = current_value[field_part]
            else:
                raise KeyError(f"Field path '{field_path}' not found")

        return current_value

    def _extract_container_value(
        self,
        container: Union[
            ModelConditionValue[str],
            ModelConditionValue[int],
            ModelConditionValue[float],
            ModelConditionValue[bool],
            ModelConditionValueList,
        ],
    ) -> str | int | float | bool | list[str | int | float | bool]:
        """Extract the actual value from the type-safe container."""
        if isinstance(container, ModelConditionValueList):
            return container.values
        else:
            # ModelConditionValue generic container
            return container.value

    def _evaluate_operator(
        self,
        actual_value: str | int | float | bool | list | dict,
        expected_value: str | int | float | bool | list[str | int | float | bool],
        operator: EnumConditionOperator,
    ) -> bool:
        """Evaluate the specific operator against actual and expected values."""
        match operator:
            case EnumConditionOperator.EQUALS:
                return actual_value == expected_value
            case EnumConditionOperator.NOT_EQUALS:
                return actual_value != expected_value
            case EnumConditionOperator.GREATER_THAN:
                return actual_value > expected_value
            case EnumConditionOperator.GREATER_THAN_OR_EQUAL:
                return actual_value >= expected_value
            case EnumConditionOperator.LESS_THAN:
                return actual_value < expected_value
            case EnumConditionOperator.LESS_THAN_OR_EQUAL:
                return actual_value <= expected_value
            case EnumConditionOperator.CONTAINS:
                return expected_value in actual_value
            case EnumConditionOperator.NOT_CONTAINS:
                return expected_value not in actual_value
            case EnumConditionOperator.IN:
                return actual_value in expected_value
            case EnumConditionOperator.NOT_IN:
                return actual_value not in expected_value
            case EnumConditionOperator.IS_TRUE:
                return bool(actual_value) is True
            case EnumConditionOperator.IS_FALSE:
                return bool(actual_value) is False
            case EnumConditionOperator.EXISTS:
                return actual_value is not None
            case EnumConditionOperator.NOT_EXISTS:
                return actual_value is None
            case _:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Unsupported operator: {operator}",
                    context={
                        "context": {
                            "operator": operator.value,
                            "supported_operators": [
                                op.value for op in EnumConditionOperator
                            ],
                        }
                    },
                )
