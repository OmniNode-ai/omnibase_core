"""
FSM Transition Condition Model for guard conditions.

Defines condition specifications for FSM state transitions, including
condition types, expressions, and validation logic for determining
valid state transitions.

Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelFSMTransitionCondition(BaseModel):
    """
    Condition specification for FSM state transitions.

    Defines condition types, expressions, and validation logic
    for determining valid state transitions.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Attributes:
        condition_name: Unique identifier for the condition.
        condition_type: Type of condition (e.g., "expression", "custom").
        expression: 3-token expression in format "field operator value".
            Valid operators: ==, !=, <, >, <=, >=, in, not_in, contains, matches.
        required: If False, evaluation errors are treated as False result.
        error_message: Custom error message for validation failures.
        retry_count: Reserved for v1.1+ (parsed but not executed).
        timeout_ms: Reserved for v1.1+ (parsed but not executed).

    v1.0 Reserved Fields (parsed but NOT executed):
        - retry_count: Parsed, but condition retry NOT executed until v1.1
        - timeout_ms: Parsed, but condition timeout NOT executed until v1.1

    Setting these fields in v1.0 contracts will NOT change runtime behavior.

    Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md
    """

    condition_name: str = Field(
        default=...,
        description="Unique condition identifier",
    )

    condition_type: str = Field(
        default=...,
        description="Type of condition (expression, custom)",
    )

    expression: str = Field(
        default=...,
        description=(
            "3-token expression in format 'field operator value'. "
            "Valid operators: ==, !=, <, >, <=, >=, in, not_in, contains, matches"
        ),
    )

    required: bool = Field(
        default=True,
        description="If false, errors treated as False",
    )

    error_message: str | None = Field(
        default=None,
        description="Custom error message",
    )

    retry_count: int | None = Field(
        default=None,
        ge=0,
        description="Reserved for v1.1+",
    )

    timeout_ms: int | None = Field(
        default=None,
        gt=0,
        description="Reserved for v1.1+",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        frozen=True,
        from_attributes=True,
    )

    # Valid operators for expression evaluation
    # Must be kept in sync with fsm_expression_parser.SUPPORTED_OPERATORS
    # and fsm_executor._evaluate_single_condition()
    VALID_OPERATORS: frozenset[str] = frozenset(
        {
            # Equality operators (symbolic and textual)
            "==",
            "!=",
            "equals",
            "not_equals",
            # Comparison operators (symbolic and textual)
            "<",
            ">",
            "<=",
            ">=",
            "greater_than",
            "less_than",
            "greater_than_or_equal",
            "less_than_or_equal",
            # Length operators
            "min_length",
            "max_length",
            # Existence operators
            "exists",
            "not_exists",
            # Containment operators
            "in",
            "not_in",
            "contains",
            # Pattern matching
            "matches",
        }
    )

    @model_validator(mode="after")
    def validate_expression_format(self) -> Self:
        """Validate that expression has exactly 3 tokens and valid operator.

        Expression format must be: "field operator value"
        Examples: "status == active", "count > 0", "name != empty",
                  "status equals ready", "items min_length 1"

        Valid operators:
        - Equality: ==, !=, equals, not_equals
        - Comparison: <, >, <=, >=, greater_than, less_than,
          greater_than_or_equal, less_than_or_equal
        - Length: min_length, max_length
        - Existence: exists, not_exists
        - Containment: in, not_in, contains
        - Pattern: matches

        Returns:
            Self: The validated model instance.

        Raises:
            ModelOnexError: If expression does not have exactly 3 tokens
                or if the operator is not in the valid operators whitelist.
        """
        tokens = self.expression.split()
        if len(tokens) != 3:
            raise ModelOnexError(
                message=(
                    f"Expression must have exactly 3 tokens (field operator value), "
                    f"got {len(tokens)} tokens: '{self.expression}'"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "condition_name": self.condition_name,
                    "expression": self.expression,
                    "token_count": len(tokens),
                },
            )

        # Validate operator is in whitelist
        operator = tokens[1]
        if operator not in self.VALID_OPERATORS:
            raise ModelOnexError(
                message=(
                    f"Invalid operator '{operator}'. "
                    f"Valid operators: {', '.join(sorted(self.VALID_OPERATORS))}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "condition_name": self.condition_name,
                    "expression": self.expression,
                    "operator": operator,
                    "valid_operators": sorted(self.VALID_OPERATORS),
                },
            )

        return self

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Note: In v1.0, this method returns True without modification.
        The model is frozen (immutable) for thread safety.
        Full execution logic is reserved for v1.1+.

        Args:
            **kwargs: Execution parameters (reserved for v1.1+).

        Returns:
            bool: Always returns True in v1.0.
        """
        # v1.1+ reserved: Implement full execution logic with retry and timeout
        # Model is frozen, so setattr is not allowed. Execution behavior
        # reserved for v1.1+ when proper state management is implemented.
        _ = kwargs  # Explicitly mark as unused
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol).

        Returns:
            dict[str, object]: Dictionary representation of the model.
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Performs validation of the condition instance:
        - Verifies required fields are non-empty
        - Validates expression format (3 tokens)

        Returns:
            bool: True if validation passes, False otherwise.

        Raises:
            ModelOnexError: If validation fails and required=True.
        """
        # Validate condition_name is non-empty
        if not self.condition_name or not self.condition_name.strip():
            if self.required:
                raise ModelOnexError(
                    message="condition_name cannot be empty",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    context={"condition_name": self.condition_name},
                )
            return False

        # Validate condition_type is non-empty
        if not self.condition_type or not self.condition_type.strip():
            if self.required:
                raise ModelOnexError(
                    message="condition_type cannot be empty",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    context={"condition_type": self.condition_type},
                )
            return False

        # Validate expression is non-empty and has correct format
        if not self.expression or not self.expression.strip():
            if self.required:
                raise ModelOnexError(
                    message="expression cannot be empty",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    context={"expression": self.expression},
                )
            return False

        # Expression format is already validated by model_validator
        # but we check token count here for explicit validation calls
        tokens = self.expression.split()
        if len(tokens) != 3:
            if self.required:
                raise ModelOnexError(
                    message=(
                        f"Expression must have exactly 3 tokens, "
                        f"got {len(tokens)}: '{self.expression}'"
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    context={
                        "expression": self.expression,
                        "token_count": len(tokens),
                    },
                )
            return False

        return True


# Export for use
__all__ = ["ModelFSMTransitionCondition"]
