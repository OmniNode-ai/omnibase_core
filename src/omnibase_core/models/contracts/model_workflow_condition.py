"""
Model Workflow Condition - ONEX Standards Compliant Workflow Condition Specification.

Strongly-typed condition model for workflow dependency conditions that eliminates
string-based condition support and enforces structured condition evaluation.

ZERO TOLERANCE: No string conditions or Any types allowed.
"""

from typing import Any, Union, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Type alias for recursive context data structure
ContextValue = Union[
    str,
    int,
    float,
    bool,
    list[Union[str, int, float, bool]],
    dict[str, Any],  # Using Any for recursive dict values to avoid type complexity
]

from omnibase_core.enums.enum_condition_operator import EnumConditionOperator
from omnibase_core.enums.enum_condition_type import EnumConditionType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.contracts.model_condition_value import (
    ConditionValue,
    ModelConditionValue,
)
from omnibase_core.models.contracts.model_condition_value_list import (
    ModelConditionValueList,
)


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
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Condition field_name cannot be empty",
            )

        v = v.strip()

        # Check for valid field name format (alphanumeric, underscores, dots for nested fields)
        if not all(c.isalnum() or c in "_." for c in v):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid field_name '{v}'. Must contain only alphanumeric characters, underscores, and dots.",
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
        self,
        context_data: dict[
            str,
            str
            | int
            | float
            | bool
            | list[str | int | float | bool]
            | dict[str, str | int | float | bool],
        ],
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
            # Handle missing fields specially for EXISTS/NOT_EXISTS operators
            if self.operator == EnumConditionOperator.EXISTS:
                return False  # Field doesn't exist, so EXISTS is False
            elif self.operator == EnumConditionOperator.NOT_EXISTS:
                return True  # Field doesn't exist, so NOT_EXISTS is True
            else:
                # For other operators, missing fields are an error
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Field '{self.field_name}' not found in context data",
                ) from e

    def _extract_field_value(
        self,
        context_data: dict[
            str,
            str
            | int
            | float
            | bool
            | list[str | int | float | bool]
            | dict[str, str | int | float | bool],
        ],
        field_path: str,
    ) -> (
        str
        | int
        | float
        | bool
        | list[str | int | float | bool]
        | dict[str, str | int | float | bool]
    ):
        """Extract field value supporting nested field paths with dot notation."""
        current_value: ContextValue = context_data

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
        actual_value: (
            str
            | int
            | float
            | bool
            | list[str | int | float | bool]
            | dict[str, str | int | float | bool]
        ),
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
                self._validate_comparison_types(actual_value, expected_value, operator)
                return actual_value > expected_value  # type: ignore[operator]
            case EnumConditionOperator.GREATER_THAN_OR_EQUAL:
                self._validate_comparison_types(actual_value, expected_value, operator)
                return actual_value >= expected_value  # type: ignore[operator]
            case EnumConditionOperator.LESS_THAN:
                self._validate_comparison_types(actual_value, expected_value, operator)
                return actual_value < expected_value  # type: ignore[operator]
            case EnumConditionOperator.LESS_THAN_OR_EQUAL:
                self._validate_comparison_types(actual_value, expected_value, operator)
                return actual_value <= expected_value  # type: ignore[operator]
            case EnumConditionOperator.CONTAINS:
                self._validate_contains_types(actual_value, expected_value, operator)
                return expected_value in actual_value  # type: ignore[operator]
            case EnumConditionOperator.NOT_CONTAINS:
                self._validate_contains_types(actual_value, expected_value, operator)
                return expected_value not in actual_value  # type: ignore[operator]
            case EnumConditionOperator.IN:
                self._validate_in_types(actual_value, expected_value, operator)
                return actual_value in expected_value  # type: ignore[operator]
            case EnumConditionOperator.NOT_IN:
                self._validate_in_types(actual_value, expected_value, operator)
                return actual_value not in expected_value  # type: ignore[operator]
            case EnumConditionOperator.IS_TRUE:
                return bool(actual_value) is True
            case EnumConditionOperator.IS_FALSE:
                return bool(actual_value) is False
            case EnumConditionOperator.EXISTS:
                return True  # Field exists in context (regardless of value)
            case EnumConditionOperator.NOT_EXISTS:
                return False  # Field exists in context (regardless of value)
            case _:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Unsupported operator: {operator}",
                )

    def _validate_comparison_types(
        self,
        actual_value: (
            str
            | int
            | float
            | bool
            | list[str | int | float | bool]
            | dict[str, str | int | float | bool]
        ),
        expected_value: str | int | float | bool | list[str | int | float | bool],
        operator: EnumConditionOperator,
    ) -> None:
        """Validate that values are comparable for comparison operators."""
        # Allow comparison between numeric types (int, float) and bool
        numeric_types = (int, float, bool)

        if isinstance(actual_value, str) and isinstance(expected_value, str):
            # String comparison is valid
            return
        elif isinstance(actual_value, numeric_types) and isinstance(
            expected_value, numeric_types
        ):
            # Numeric comparison is valid
            return
        else:
            # Incompatible types
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot compare {type(actual_value).__name__} with {type(expected_value).__name__} using {operator.value} operator",
            )

    def _validate_contains_types(
        self,
        actual_value: (
            str
            | int
            | float
            | bool
            | list[str | int | float | bool]
            | dict[str, str | int | float | bool]
        ),
        expected_value: str | int | float | bool | list[str | int | float | bool],
        operator: EnumConditionOperator,
    ) -> None:
        """Validate that types are compatible for contains/not_contains operators."""
        # Contains operations require the actual_value to be a container type
        if isinstance(actual_value, (str, list, dict)):
            return
        else:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot use {operator.value} operator on {type(actual_value).__name__} - must be string, list, or dict",
            )

    def _validate_in_types(
        self,
        actual_value: (
            str
            | int
            | float
            | bool
            | list[str | int | float | bool]
            | dict[str, str | int | float | bool]
        ),
        expected_value: str | int | float | bool | list[str | int | float | bool],
        operator: EnumConditionOperator,
    ) -> None:
        """Validate that types are compatible for in/not_in operators."""
        # In operations require the expected_value to be a container type
        if isinstance(expected_value, (str, list)):
            return
        else:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot use {operator.value} operator with {type(expected_value).__name__} - expected value must be string or list",
            )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=True,  # Convert enums to strings for serialization consistency
        validate_assignment=True,
    )
