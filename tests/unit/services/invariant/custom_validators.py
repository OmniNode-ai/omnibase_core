# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Custom validators for testing custom invariant evaluation.

This module provides sample validator functions that demonstrate the
different signatures and behaviors supported by CUSTOM invariant type.

Validator Signatures:
    1. tuple[bool, str] - Returns (passed, message)
    2. bool - Returns only pass/fail status (message auto-generated)

Thread Safety:
    All validator functions in this module are stateless and thread-safe.
"""

from typing import Any


def always_pass(output: dict[str, Any]) -> tuple[bool, str]:
    """Validator that always passes.

    Args:
        output: The output dictionary to validate (unused).

    Returns:
        Tuple of (True, success message).
    """
    return True, "Always passes"


def always_fail(output: dict[str, Any]) -> tuple[bool, str]:
    """Validator that always fails.

    Args:
        output: The output dictionary to validate (unused).

    Returns:
        Tuple of (False, failure message).
    """
    return False, "Always fails"


def check_has_data(output: dict[str, Any]) -> tuple[bool, str]:
    """Check if output has 'data' field.

    Args:
        output: The output dictionary to validate.

    Returns:
        Tuple of (passed, message) indicating if 'data' key exists.
    """
    if "data" in output:
        return True, "Data field present"
    return False, "Missing data field"


def raise_exception(output: dict[str, Any]) -> tuple[bool, str]:
    """Validator that raises an exception.

    Used for testing exception handling in custom callable evaluation.

    Args:
        output: The output dictionary to validate (unused).

    Raises:
        ValueError: Always raises this exception for testing.
    """
    raise ValueError("Intentional test exception")


def return_bool_only(output: dict[str, Any]) -> bool:
    """Validator that returns only bool (alternative signature).

    Demonstrates the simpler return signature where only a boolean
    is returned, and the message is auto-generated.

    Args:
        output: The output dictionary to validate.

    Returns:
        True if 'valid' key exists in output, False otherwise.
    """
    return "valid" in output
