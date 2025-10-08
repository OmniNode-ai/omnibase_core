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
    """

    file_path: str
    line_number: int
    column_number: int
    function_name: str
    module_name: str
    stack_trace: str
    additional_context: dict[str, Any]
