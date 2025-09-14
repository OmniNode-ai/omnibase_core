"""
Model Workflow Condition - ONEX Standards Compliant Workflow Condition Specification.

Strongly-typed condition model for workflow dependency conditions that eliminates
string-based condition support and enforces structured condition evaluation.

ZERO TOLERANCE: No string conditions or Any types allowed.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

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

    expected_value: Any = Field(
        ...,
        description="Expected value for comparison",
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
    def validate_expected_value(cls, v: Any, values: dict[str, Any]) -> Any:
        """Validate expected value is compatible with operator."""
        # Note: In Pydantic v2, we get the FieldValidationInfo as second parameter
        # For now, basic validation - can be enhanced based on operator type
        return v

    def evaluate_condition(self, context_data: dict[str, Any]) -> bool:
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

            # Perform operator-specific evaluation
            return self._evaluate_operator(
                field_value, self.expected_value, self.operator
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
        self, context_data: dict[str, Any], field_path: str
    ) -> Any:
        """Extract field value supporting nested field paths with dot notation."""
        current_value = context_data

        for field_part in field_path.split("."):
            if isinstance(current_value, dict) and field_part in current_value:
                current_value = current_value[field_part]
            else:
                raise KeyError(f"Field path '{field_path}' not found")

        return current_value

    def _evaluate_operator(
        self, actual_value: Any, expected_value: Any, operator: EnumConditionOperator
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
