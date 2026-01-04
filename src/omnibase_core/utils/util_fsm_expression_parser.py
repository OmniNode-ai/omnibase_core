"""
FSM Expression Parser for declarative state machine conditions.

Parses 3-token FSM condition expressions used in FSM transitions.
Strictly enforces "field operator value" grammar for predictable parsing.

Usage:
    >>> from omnibase_core.utils.util_fsm_expression_parser import parse_expression
    >>> field, operator, value = parse_expression("count equals 5")
    >>> print(field, operator, value)
    count equals 5

    >>> parse_expression("name exists _")
    ('name', 'exists', '_')

    >>> parse_expression("too many tokens here")  # Raises ModelOnexError

Security:
    Field names are validated to prevent access to private/internal context fields.
    By default, field names starting with underscore(s) are rejected.
    Use allow_private_fields=True to allow underscore-prefixed fields if needed.
"""

from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Supported operators for FSM condition expressions
# These correspond to operators used in fsm_executor._evaluate_single_condition()
SUPPORTED_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        # Equality operators (textual)
        "equals",
        "not_equals",
        # Equality operators (symbolic)
        "==",
        "!=",
        # Comparison operators (textual)
        "greater_than",
        "less_than",
        "greater_than_or_equal",
        "less_than_or_equal",
        # Comparison operators (symbolic)
        ">",
        "<",
        ">=",
        "<=",
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


def _validate_field_name(
    field: str, expression: str, *, allow_private_fields: bool = False
) -> None:
    """
    Validate a field name for security and correctness.

    Args:
        field: The field name to validate
        expression: The original expression (for error context)
        allow_private_fields: If True, allows underscore-prefixed fields

    Raises:
        ModelOnexError: If field name is invalid
    """
    # Check for empty field name
    if not field:
        raise ModelOnexError(
            message="Field name cannot be empty",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            expression=expression,
            field=field,
        )

    # Security check: reject underscore-prefixed fields by default
    # This prevents unintended access to private/internal context fields like
    # __class__, __dict__, _internal_field, etc.
    if not allow_private_fields:
        # Check if field or any segment starts with underscore
        if field.startswith("_"):
            raise ModelOnexError(
                message=(
                    f"Field name '{field}' cannot start with underscore. "
                    "Underscore-prefixed fields are restricted for security. "
                    "Use allow_private_fields=True if access to private fields is "
                    "intentionally required."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                expression=expression,
                field=field,
            )

        # For nested paths like user.email, check each segment
        if "." in field:
            segments = field.split(".")
            for segment in segments:
                if not segment:
                    raise ModelOnexError(
                        message=(
                            f"Field name '{field}' contains empty segment. "
                            "Field paths cannot have consecutive dots or start/end with dots."
                        ),
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        expression=expression,
                        field=field,
                    )
                if segment.startswith("_"):
                    raise ModelOnexError(
                        message=(
                            f"Field segment '{segment}' in '{field}' cannot start with "
                            "underscore. Underscore-prefixed fields are restricted for security. "
                            "Use allow_private_fields=True if access to private fields is "
                            "intentionally required."
                        ),
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        expression=expression,
                        field=field,
                        invalid_segment=segment,
                    )


def parse_expression(
    expression: str, *, allow_private_fields: bool = False
) -> tuple[str, str, str]:
    """
    Parse a 3-token FSM condition expression.

    Format: "field operator value"

    The expression must have exactly 3 whitespace-separated tokens:
    1. field: The context field name to evaluate
    2. operator: The comparison operator (must be in SUPPORTED_OPERATORS)
    3. value: The expected value to compare against (use "_" for existence checks)

    Security:
        By default, field names starting with underscore(s) are rejected to prevent
        unintended access to private/internal context fields (e.g., __class__, _internal).
        Use allow_private_fields=True if access to underscore-prefixed fields is
        intentionally required.

    Args:
        expression: The expression string to parse
        allow_private_fields: If True, allows field names starting with underscore.
            Default is False for security.

    Returns:
        Tuple of (field, operator, value)

    Raises:
        ModelOnexError: If expression is empty, doesn't have exactly 3 tokens,
                       operator is not supported, or field name is invalid

    Examples:
        >>> parse_expression("count equals 5")
        ('count', 'equals', '5')

        >>> parse_expression("name exists _")
        ('name', 'exists', '_')

        >>> parse_expression("status in active,pending,processing")
        ('status', 'in', 'active,pending,processing')

        >>> parse_expression("data_count min_length 1")
        ('data_count', 'min_length', '1')

        >>> parse_expression("_private equals secret")  # Raises ModelOnexError
        >>> parse_expression("_private equals secret", allow_private_fields=True)
        ('_private', 'equals', 'secret')
    """
    # Handle empty or whitespace-only expression
    if not expression or not expression.strip():
        raise ModelOnexError(
            message="Expression cannot be empty",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            expression=expression,
        )

    # Split by whitespace (handles multiple spaces between tokens)
    tokens = expression.split()

    # Strict 3-token enforcement
    token_count = len(tokens)
    if token_count != 3:
        raise ModelOnexError(
            message=(
                f"Expression must have exactly 3 tokens (field operator value), "
                f"got {token_count}: {tokens!r}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            expression=expression,
            token_count=token_count,
            tokens=tokens,
        )

    field, operator, value = tokens

    # Validate field name (security check for underscore-prefixed fields)
    _validate_field_name(field, expression, allow_private_fields=allow_private_fields)

    # Validate operator is supported
    if operator not in SUPPORTED_OPERATORS:
        raise ModelOnexError(
            message=(
                f"Unsupported operator '{operator}'. "
                f"Supported operators: {sorted(SUPPORTED_OPERATORS)}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            expression=expression,
            operator=operator,
            supported_operators=sorted(SUPPORTED_OPERATORS),
        )

    return field, operator, value


def validate_expression(expression: str, *, allow_private_fields: bool = False) -> bool:
    """
    Validate an FSM condition expression without raising exceptions.

    Useful for pre-validation where you want a boolean result instead of exceptions.

    Args:
        expression: The expression string to validate
        allow_private_fields: If True, allows field names starting with underscore.
            Default is False for security.

    Returns:
        True if expression is valid, False otherwise

    Examples:
        >>> validate_expression("count equals 5")
        True

        >>> validate_expression("too many tokens here")
        False

        >>> validate_expression("")
        False

        >>> validate_expression("_private equals secret")
        False

        >>> validate_expression("_private equals secret", allow_private_fields=True)
        True
    """
    try:
        parse_expression(expression, allow_private_fields=allow_private_fields)
        return True
    except ModelOnexError:
        return False


def get_supported_operators() -> frozenset[str]:
    """
    Get the set of supported operators.

    Returns:
        Frozen set of supported operator strings

    Examples:
        >>> operators = get_supported_operators()
        >>> "equals" in operators
        True
        >>> "invalid_op" in operators
        False
    """
    return SUPPORTED_OPERATORS


# Public API
__all__ = [
    "SUPPORTED_OPERATORS",
    "get_supported_operators",
    "parse_expression",
    "validate_expression",
]
