"""TypedDictBasicErrorContext.

Minimal error context TypedDict with no dependencies.

This is a simple type definition used by ModelOnexError to avoid
circular dependencies with ModelErrorContext.
"""

from __future__ import annotations

from typing import Any, TypedDict


class TypedDictBasicErrorContext(TypedDict, total=False):
    """
    Minimal error context with no dependencies.

    This is a simple type definition used by ModelOnexError to avoid
    circular dependencies with ModelErrorContext.

    All fields are optional (total=False) to match the original dataclass behavior.

    Attributes:
        file_path: Path to the file where the error occurred
        line_number: Line number where the error occurred
        column_number: Column number where the error occurred
        function_name: Name of the function where the error occurred
        module_name: Name of the module where the error occurred
        stack_trace: Full stack trace of the error
        rollback_errors: List of error messages from failed rollback operations
        additional_context: Additional contextual information about the error
    """

    file_path: str
    line_number: int
    column_number: int
    function_name: str
    module_name: str
    stack_trace: str
    rollback_errors: list[str]
    additional_context: dict[str, Any]


__all__ = ["TypedDictBasicErrorContext"]
