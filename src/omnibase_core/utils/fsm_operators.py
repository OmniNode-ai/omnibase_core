"""
FSM string comparison operators for condition evaluation.

This module provides string-based comparison operators for evaluating
FSM transition conditions. All operators use STRING COERCION by design
to ensure consistent behavior with YAML/JSON configuration values.

Type Coercion Philosophy:
    FSM conditions are typically defined in YAML/JSON where all values
    are strings. String coercion ensures consistent behavior regardless
    of the value source (config file vs runtime context).

    This is INTENTIONAL behavior, not a bug. If you need type-aware
    comparison, preprocess your context values or use numeric operators
    (greater_than, less_than) which preserve numeric semantics.

Examples:
    >>> evaluate_equals("hello", "hello")
    True
    >>> evaluate_equals(1, "1")
    True  # Type coercion: both become "1"
    >>> evaluate_equals(None, "None")
    True  # None becomes "None"
    >>> evaluate_not_equals("a", "b")
    True

Type Coercion Footguns (documented behavior):
    - 1 equals "1" -> True (integer coerced to string)
    - None equals "None" -> True (None becomes "None")
    - True equals "True" -> True (boolean becomes "True")
    - False equals "False" -> True (boolean becomes "False")
    - [1, 2] equals "[1, 2]" -> True (list repr)
    - {"a": 1} equals "{'a': 1}" -> True (dict repr)
    - 0 equals "0" -> True (zero coerced to string)
    - 0 equals "" -> False (empty string != "0")
    - None equals "" -> False ("None" != "")

See Also:
    - fsm_executor.py: Uses these operators for condition evaluation
    - ModelFSMTransitionCondition: Defines condition expressions
"""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


def evaluate_equals(lhs: object, rhs: object) -> bool:
    """
    Evaluate equals operator with string coercion.

    Both sides are coerced to string before comparison. This is
    INTENTIONAL to ensure consistent behavior with YAML/JSON
    configuration values where all values are strings.

    Type Coercion Behavior:
        - None becomes "None"
        - Numbers become their string representation
        - Booleans become "True" or "False"
        - Lists/dicts become their repr() string
        - 1 equals "1" is True (type coercion!)

    Args:
        lhs: Left-hand side value (typically from FSM context)
        rhs: Right-hand side value (typically from expression/config)

    Returns:
        True if str(lhs) == str(rhs), False otherwise

    Examples:
        >>> evaluate_equals("hello", "hello")
        True
        >>> evaluate_equals(1, "1")
        True
        >>> evaluate_equals(None, "None")
        True
        >>> evaluate_equals(True, "True")
        True
        >>> evaluate_equals([1, 2], "[1, 2]")
        True
        >>> evaluate_equals("a", "b")
        False

    Warning:
        Type information is LOST during comparison. If you need
        type-aware comparison, preprocess your values or use
        numeric operators (greater_than, less_than).
    """
    return str(lhs) == str(rhs)


def evaluate_not_equals(lhs: object, rhs: object) -> bool:
    """
    Evaluate not_equals operator with string coercion.

    Both sides are coerced to string before comparison. This is
    INTENTIONAL to ensure consistent behavior with YAML/JSON
    configuration values.

    Type Coercion Behavior:
        - None becomes "None"
        - Numbers become their string representation
        - Booleans become "True" or "False"
        - Lists/dicts become their repr() string
        - 1 not_equals "1" is False (type coercion!)

    Args:
        lhs: Left-hand side value (typically from FSM context)
        rhs: Right-hand side value (typically from expression/config)

    Returns:
        True if str(lhs) != str(rhs), False otherwise

    Examples:
        >>> evaluate_not_equals("a", "b")
        True
        >>> evaluate_not_equals(1, 2)
        True
        >>> evaluate_not_equals("hello", "hello")
        False
        >>> evaluate_not_equals(1, "1")
        False  # Type coercion: both become "1"

    Warning:
        Type information is LOST during comparison. If you need
        type-aware comparison, preprocess your values or use
        numeric operators.
    """
    return str(lhs) != str(rhs)


# Supported string operators for dispatch
_STRING_OPERATORS: frozenset[str] = frozenset({"equals", "==", "not_equals", "!="})


def is_string_operator(operator: str) -> bool:
    """
    Check if an operator is a string comparison operator.

    Args:
        operator: The operator name to check

    Returns:
        True if operator is a string operator, False otherwise

    Examples:
        >>> is_string_operator("equals")
        True
        >>> is_string_operator("==")
        True
        >>> is_string_operator("not_equals")
        True
        >>> is_string_operator("!=")
        True
        >>> is_string_operator("greater_than")
        False
    """
    return operator in _STRING_OPERATORS


def evaluate_string_operator(
    operator: str,
    lhs: object,
    rhs: object,
) -> bool:
    """
    Evaluate a string comparison operator.

    Dispatches to the appropriate evaluation function based on
    the operator name. Supports both symbolic (==, !=) and
    named (equals, not_equals) operator forms.

    Args:
        operator: The operator name ("equals", "==", "not_equals", "!=")
        lhs: Left-hand side value
        rhs: Right-hand side value

    Returns:
        Result of the comparison

    Raises:
        ModelOnexError: If operator is not a valid string operator

    Examples:
        >>> evaluate_string_operator("equals", "hello", "hello")
        True
        >>> evaluate_string_operator("==", 1, "1")
        True
        >>> evaluate_string_operator("not_equals", "a", "b")
        True
        >>> evaluate_string_operator("!=", "x", "y")
        True

    See Also:
        - evaluate_equals: For equals/== operator
        - evaluate_not_equals: For not_equals/!= operator
        - is_string_operator: To check if operator is valid
    """
    if operator in ("equals", "=="):
        return evaluate_equals(lhs, rhs)
    elif operator in ("not_equals", "!="):
        return evaluate_not_equals(lhs, rhs)
    else:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown string operator: {operator}",
            context={
                "operator": operator,
                "valid_operators": list(_STRING_OPERATORS),
            },
        )


# Public API
__all__ = [
    "evaluate_equals",
    "evaluate_not_equals",
    "evaluate_string_operator",
    "is_string_operator",
]
