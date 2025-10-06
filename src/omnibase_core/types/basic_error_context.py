"""BasicErrorContext.

Minimal error context with no dependencies.

This is a simple data container used by ModelOnexError to avoid
circular dependencies with ModelErrorContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BasicErrorContext:
    """
    Minimal error context with no dependencies.

    This is a simple data container used by ModelOnexError to avoid
    circular dependencies with ModelErrorContext.

    Attributes:
        file_path: Optional file path where error occurred
        line_number: Optional line number where error occurred
        column_number: Optional column number where error occurred
        function_name: Optional function name where error occurred
        module_name: Optional module name where error occurred
        stack_trace: Optional stack trace
        additional_context: Additional context as key-value pairs
    """

    file_path: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    function_name: str | None = None
    module_name: str | None = None
    stack_trace: str | None = None
    additional_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict[str, Any]ionary representation."""
        result: dict[str, Any] = {}

        # Add non-None standard fields
        if self.file_path is not None:
            result["file_path"] = self.file_path
        if self.line_number is not None:
            result["line_number"] = self.line_number
        if self.column_number is not None:
            result["column_number"] = self.column_number
        if self.function_name is not None:
            result["function_name"] = self.function_name
        if self.module_name is not None:
            result["module_name"] = self.module_name
        if self.stack_trace is not None:
            result["stack_trace"] = self.stack_trace

        # Add additional context
        result.update(self.additional_context)

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BasicErrorContext:
        """Create from dict[str, Any]ionary representation."""
        # Extract known fields
        known_fields = {
            "file_path": data.get("file_path"),
            "line_number": data.get("line_number"),
            "column_number": data.get("column_number"),
            "function_name": data.get("function_name"),
            "module_name": data.get("module_name"),
            "stack_trace": data.get("stack_trace"),
        }

        # Extract additional context (everything else)
        additional_context = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            **{k: v for k, v in known_fields.items() if v is not None},
            additional_context=additional_context,
        )
