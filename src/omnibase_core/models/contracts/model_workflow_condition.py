"""
Model Workflow Condition Specification.

Strongly-typed condition model for workflow dependency conditions that eliminates
string-based condition support and enforces structured condition evaluation.

Strict typing is enforced: No string conditions or Any types allowed.
"""

from typing import cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_condition_operator import EnumConditionOperator
from omnibase_core.enums.enum_condition_type import EnumConditionType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_condition_value_list import (
    ModelConditionValueList,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.security.model_condition_value import ModelConditionValue
from omnibase_core.types.type_constraints import (
    ComplexContextValueType,
    ContextValueType,
    PrimitiveValueType,
    is_primitive_value,
)

# Type alias for condition value that can be single or list
ConditionValueType = PrimitiveValueType | list[PrimitiveValueType]


class ModelWorkflowCondition(BaseModel):
    """
    Strongly-typed workflow condition specification.

    Replaces string-based conditions with structured condition evaluation
    that enables proper validation, type safety, and architectural consistency.

    Strict typing is enforced: No string conditions or Any types allowed.
    """

    condition_type: EnumConditionType = Field(
        default=...,
        description="Type of condition to evaluate",
    )

    field_name: str = Field(
        default=...,
        description="Name of the field or property to evaluate",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    operator: EnumConditionOperator = Field(
        default=...,
        description="Operator to use for condition evaluation",
    )

    expected_value: ModelConditionValue | ModelConditionValueList = Field(
        default=...,
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
            raise ModelOnexError(
                message="Condition field_name cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        v = v.strip()

        # Check for valid field name format (alphanumeric, underscores, dots for nested fields)
        if not all(c.isalnum() or c in "_." for c in v):
            raise ModelOnexError(
                message=f"Invalid field_name '{v}'. Must contain only alphanumeric characters, underscores, and dots.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return v

    @field_validator("expected_value")
    @classmethod
    def validate_expected_value(
        cls,
        v: object,
        info: ValidationInfo | None = None,
    ) -> object:
        """Validate expected value container is properly typed and compatible with operator."""
        # Validation is handled by the container types themselves
        # Additional operator compatibility checks can be added based on info.data
        return v

    def evaluate_condition(
        self,
        context_data: dict[str, ContextValueType],
    ) -> bool:
        """
        Evaluate the condition against provided context data.

        Args:
            context_data: Data context for condition evaluation

        Returns:
            True if condition is satisfied, False otherwise

        Raises:
            ModelOnexError: If evaluation fails due to missing data or invalid operators
        """
        try:
            # Extract field value from context
            field_value = self._extract_field_value(context_data, self.field_name)

            # Extract the actual value from the container
            expected_actual_value = self._extract_container_value(self.expected_value)

            # Perform operator-specific evaluation
            return self._evaluate_operator(
                field_value,
                expected_actual_value,
                self.operator,
            )

        except KeyError as e:
            # Handle missing fields specially for EXISTS/NOT_EXISTS operators
            if self.operator == EnumConditionOperator.EXISTS:
                return False  # Field doesn't exist, so EXISTS is False
            if self.operator == EnumConditionOperator.NOT_EXISTS:
                return True  # Field doesn't exist, so NOT_EXISTS is True
            # For other operators, missing fields are an error
            raise ModelOnexError(
                message=f"Field '{self.field_name}' not found in context data",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def _extract_field_value(
        self,
        context_data: dict[str, ContextValueType],
        field_path: str,
    ) -> ContextValueType:
        """Extract field value supporting nested field paths with dot notation."""
        current_value: ComplexContextValueType = cast(
            "ComplexContextValueType",
            context_data,
        )

        for field_part in field_path.split("."):
            if isinstance(current_value, dict) and field_part in current_value:
                current_value = current_value[field_part]
            else:
                # error-ok: KeyError is caught by caller to handle EXISTS/NOT_EXISTS operators
                raise KeyError(f"Field path '{field_path}' not found")

        # Return the extracted value
        return current_value

    def _extract_container_value(
        self,
        container: ModelConditionValue | ModelConditionValueList,
    ) -> ConditionValueType:
        """Extract the actual value from the type-safe container."""
        if isinstance(container, ModelConditionValueList):
            return container.values
        if hasattr(container, "value"):
            # ModelConditionValue generic container - type guard for .value attribute
            return cast("ConditionValueType", container.value)
        raise ModelOnexError(
            message=f"Invalid container type: {type(container).__name__}. Expected ModelConditionValue or ModelConditionValueList.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def _evaluate_operator(
        self,
        actual_value: ContextValueType,
        expected_value: ConditionValueType,
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
                # NOTE(OMN-1302): Operand types validated by _validate_comparison_types above. Safe because numeric/string comparison validated at runtime.
                return actual_value > expected_value  # type: ignore[operator]
            case EnumConditionOperator.GREATER_THAN_OR_EQUAL:
                self._validate_comparison_types(actual_value, expected_value, operator)
                # NOTE(OMN-1302): Operand types validated by _validate_comparison_types above. Safe because numeric/string comparison validated at runtime.
                return actual_value >= expected_value  # type: ignore[operator]
            case EnumConditionOperator.LESS_THAN:
                self._validate_comparison_types(actual_value, expected_value, operator)
                # NOTE(OMN-1302): Operand types validated by _validate_comparison_types above. Safe because numeric/string comparison validated at runtime.
                return actual_value < expected_value  # type: ignore[operator]
            case EnumConditionOperator.LESS_THAN_OR_EQUAL:
                self._validate_comparison_types(actual_value, expected_value, operator)
                # NOTE(OMN-1302): Operand types validated by _validate_comparison_types above. Safe because numeric/string comparison validated at runtime.
                return actual_value <= expected_value  # type: ignore[operator]
            case EnumConditionOperator.CONTAINS:
                self._validate_contains_types(actual_value, expected_value, operator)
                # NOTE(OMN-1302): Container type validated by _validate_contains_types above. Safe because str/list/dict membership check validated at runtime.
                return expected_value in actual_value  # type: ignore[operator]
            case EnumConditionOperator.NOT_CONTAINS:
                self._validate_contains_types(actual_value, expected_value, operator)
                # NOTE(OMN-1302): Container type validated by _validate_contains_types above. Safe because str/list/dict membership check validated at runtime.
                return expected_value not in actual_value  # type: ignore[operator]
            case EnumConditionOperator.IN:
                self._validate_in_types(actual_value, expected_value, operator)
                # NOTE(OMN-1302): Collection type validated by _validate_in_types above. Safe because str/list membership check validated at runtime.
                return actual_value in expected_value  # type: ignore[operator]
            case EnumConditionOperator.NOT_IN:
                self._validate_in_types(actual_value, expected_value, operator)
                # NOTE(OMN-1302): Collection type validated by _validate_in_types above. Safe because str/list membership check validated at runtime.
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
                raise ModelOnexError(
                    message=f"Unsupported operator: {operator}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

    def _validate_comparison_types(
        self,
        actual_value: ContextValueType,
        expected_value: ConditionValueType,
        operator: EnumConditionOperator,
    ) -> None:
        """Validate that values are comparable for comparison operators."""
        # First validate that expected_value is a primitive (not a list[Any]) for comparison
        if isinstance(expected_value, list):
            raise ModelOnexError(
                message=f"Cannot use {operator.value} operator with list[Any]type - use IN/NOT_IN operators instead",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Ensure both values are primitive types using runtime validation
        if not is_primitive_value(actual_value):
            raise ModelOnexError(
                message=f"Cannot compare non-primitive type {type(actual_value).__name__} using {operator.value} operator",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if not is_primitive_value(expected_value):
            raise ModelOnexError(
                message=f"Cannot compare with non-primitive type {type(expected_value).__name__} using {operator.value} operator",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Now we know both values are primitives, check type compatibility
        # Allow comparison between numeric types (int, float) and bool
        numeric_types = (int, float, bool)

        if isinstance(actual_value, str) and isinstance(expected_value, str):
            # String comparison is valid
            return
        if isinstance(actual_value, numeric_types) and isinstance(
            expected_value,
            numeric_types,
        ):
            # Numeric comparison is valid
            return
        # Incompatible types
        raise ModelOnexError(
            message=f"Cannot compare {type(actual_value).__name__} with {type(expected_value).__name__} using {operator.value} operator",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def _validate_contains_types(
        self,
        actual_value: ContextValueType,
        expected_value: ConditionValueType,
        operator: EnumConditionOperator,
    ) -> None:
        """Validate that types are compatible for contains/not_contains operators."""
        # Contains operations require the actual_value to be a container type
        if isinstance(actual_value, (str, list, dict)):
            # Ensure expected_value is a primitive for contains operations (not a list[Any])
            if isinstance(expected_value, list):
                raise ModelOnexError(
                    message=f"Cannot use {operator.value} operator with list[Any]as expected value - expected a single primitive value",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            return
        raise ModelOnexError(
            message=f"Cannot use {operator.value} operator on {type(actual_value).__name__} - must be string, list[Any], or dict[str, Any]",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def _validate_in_types(
        self,
        actual_value: ContextValueType,
        expected_value: ConditionValueType,
        operator: EnumConditionOperator,
    ) -> None:
        """Validate that types are compatible for in/not_in operators."""
        # In operations require the expected_value to be a container type
        if isinstance(expected_value, (str, list)):
            # Ensure actual_value is a primitive for in operations
            if not is_primitive_value(actual_value):
                raise ModelOnexError(
                    message=f"Cannot use {operator.value} operator with non-primitive actual value {type(actual_value).__name__}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            return
        raise ModelOnexError(
            message=f"Cannot use {operator.value} operator with {type(expected_value).__name__} - expected value must be string or list[Any]",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=True,  # Convert enums to strings for serialization consistency
        validate_assignment=True,
    )
