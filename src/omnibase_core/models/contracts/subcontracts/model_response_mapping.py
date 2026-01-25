"""Response mapping model for operation bindings DSL.

Defines how handler results are transformed into response fields.
Supports template expressions in string values for dynamic field mapping.

Expression format: ${root.path} or ${root.path | function}
Allowed roots: binding.config, contract.config, request, result
Allowed functions: to_json, from_json (no chaining)

VERSION: 1.0.0

Author: ONEX Framework Team
"""

from __future__ import annotations

import re
from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants.constants_effect import contains_denied_builtin
from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any


@allow_dict_any(
    reason="Response mapping fields intentionally accept arbitrary nested values "
    "(str, int, float, bool, list, dict) for DSL flexibility. String values may "
    "contain ${...} expressions that are validated at runtime."
)
class ModelResponseMapping(BaseModel):
    """
    Response field mapping for operation bindings DSL.

    Maps handler results to response fields using template expressions.
    This is a "dumb DSL" with intentional limitations for security and simplicity.

    Template values can be:
        - str: May contain ${...} template expressions
        - int, float, bool: Literal values passed through unchanged
        - list: Recursive list of template values
        - dict: Recursive dict with string keys and template values

    Expression Format:
        - ${root.path} - simple path access
        - ${root.path | function} - path with pipe function

        Allowed roots: binding.config, contract.config, request, result
        Allowed functions: to_json, from_json

    Security:
        - All expression paths are validated against DENIED_BUILTINS
        - Double underscores in paths are rejected
        - Bracket notation and ternary operators are rejected

    Example YAML:
        response:
          status: "${result.status}"
          snapshot: "${request.snapshot}"
          error_message: "${result.error_message}"
          bytes_written: "${result.bytes_written}"

    Example with nested values:
        response:
          data:
            id: "${result.id}"
            serialized: "${result.payload | to_json}"
          metadata:
            request_id: "${request.request_id}"
            timestamp: "${result.timestamp}"

    See Also:
        - ModelBindingExpression: Expression validation and parsing
        - ModelEnvelopeTemplate: Similar template model for envelope construction
    """

    # Expression pattern for finding ${...} expressions within strings.
    # Unlike ModelBindingExpression, this pattern is not anchored because
    # expressions can be embedded within larger strings.
    EXPRESSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\$\{(?P<root>binding\.config|contract\.config|request|result)"
        r"(?:\.(?P<path>[a-zA-Z_][a-zA-Z0-9_.]*))?"
        r"(?:\s*\|\s*(?P<function>to_json|from_json))?\}"
    )

    # Pattern to find any ${...} expression (for detecting potentially invalid ones)
    ANY_EXPRESSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\$\{(?P<content>[^}]+)\}"
    )

    # Allowed root prefixes for expressions
    ALLOWED_ROOTS: ClassVar[frozenset[str]] = frozenset(
        {"binding.config", "contract.config", "request", "result"}
    )

    # Allowed pipe functions
    ALLOWED_FUNCTIONS: ClassVar[frozenset[str]] = frozenset({"to_json", "from_json"})

    # Maximum recursion depth for nested value validation (prevents DoS)
    MAX_RECURSION_DEPTH: ClassVar[int] = 20

    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping of response field names to their template values",
    )
    """Mapping of response field names to their template values."""

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def validate_template_expressions(self) -> Self:
        """
        Validate any ${...} expressions in template fields.

        Recursively walks through all field values and validates that any
        string containing ${...} follows the binding expression format.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If an expression has invalid format or uses
                disallowed roots/functions.
        """
        self._validate_value(self.fields, path="fields", depth=0)
        return self

    def _validate_value(self, value: Any, path: str, depth: int) -> None:
        """
        Recursively validate template values for valid expressions.

        Args:
            value: The value to validate (may be str, dict, list, or literal).
            path: The current path for error messages.
            depth: Current recursion depth (max 20 to prevent DoS).

        Raises:
            ValueError: If a string contains an invalid ${...} expression.
        """
        # Prevent excessive recursion
        if depth > self.MAX_RECURSION_DEPTH:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Response mapping exceeds maximum nesting depth of "
                f"{self.MAX_RECURSION_DEPTH} at {path!r}"
            )

        if isinstance(value, str) and "${" in value:
            self._validate_expressions_in_string(value, path)
        elif isinstance(value, dict):
            for key, val in value.items():
                self._validate_value(val, f"{path}.{key}", depth + 1)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                self._validate_value(item, f"{path}[{idx}]", depth + 1)
        # int, float, bool, None are always valid - no validation needed

    def _validate_expressions_in_string(self, value: str, path: str) -> None:
        """
        Validate all ${...} expressions within a string.

        A string may contain multiple expressions interspersed with literal text.
        Each expression is validated independently.

        Args:
            value: The string containing one or more expressions.
            path: The field path for error messages.

        Raises:
            ValueError: If any expression in the string is invalid.
        """
        for match in self.ANY_EXPRESSION_PATTERN.finditer(value):
            content = match.group("content").strip()
            self._validate_expression_content(content, value, path)

    def _validate_expression_content(
        self, content: str, full_value: str, path: str
    ) -> None:
        """
        Validate the content of a single ${...} expression.

        Args:
            content: The content inside ${...} (e.g., "request.snapshot | to_json").
            full_value: The full string value for error context.
            path: The field path for error messages.

        Raises:
            ValueError: If the expression content is invalid.
        """
        # Check for empty expression
        if not content:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Empty expression at {path!r}: found '${{}}' in {full_value!r}"
            )

        # Check for ternary operators (CRITICAL - out of scope)
        if "?" in content and ":" in content:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Ternary operators not allowed at {path!r}: "
                f"found ternary in '${{{content}}}'"
            )

        # Check for bracket notation
        if "[" in content or "]" in content:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Bracket notation not allowed at {path!r}: "
                f"found brackets in '${{{content}}}'. Use dot-path only."
            )

        # Check for multiple pipes (chaining not allowed)
        if content.count("|") > 1:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Chained pipes not allowed at {path!r}: "
                f"found {content.count('|')} pipes in '${{{content}}}'"
            )

        # Split by pipe to get path and optional function
        parts = content.split("|")
        path_part = parts[0].strip()
        func_part = parts[1].strip() if len(parts) > 1 else None

        # Validate root
        root_valid = False
        for root in self.ALLOWED_ROOTS:
            if path_part == root or path_part.startswith(f"{root}."):
                root_valid = True
                break

        if not root_valid:
            # Provide helpful error for common mistake
            if path_part.startswith("config."):
                # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
                raise ValueError(
                    f"Ambiguous root 'config' at {path!r}: "
                    f"'{path_part}' must use 'binding.config' or 'contract.config'"
                )
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Invalid expression root at {path!r}: "
                f"'{path_part}' must start with one of {sorted(self.ALLOWED_ROOTS)}"
            )

        # Validate function if present
        if func_part is not None and func_part not in self.ALLOWED_FUNCTIONS:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Invalid pipe function at {path!r}: "
                f"'{func_part}' must be one of {sorted(self.ALLOWED_FUNCTIONS)}"
            )

        # Security: Check for double underscores
        if "__" in path_part:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Security violation at {path!r}: "
                f"double underscore not allowed in expression path: {path_part!r}"
            )

        # Security: Check for denied builtins in the path
        # Extract the part after the root (e.g., "status" from "result.status")
        for root in self.ALLOWED_ROOTS:
            if path_part == root:
                # Just the root, no additional path to check
                break
            if path_part.startswith(f"{root}."):
                # Check the path after the root
                expr_path = path_part[len(root) + 1 :]
                denied = contains_denied_builtin(expr_path)
                if denied:
                    # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
                    raise ValueError(
                        f"Security violation at {path!r}: "
                        f"forbidden identifier '{denied}' in expression path: {path_part!r}"
                    )
                break

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        field_count = len(self.fields)
        return f"ModelResponseMapping(fields={{{field_count} fields}})"


__all__ = ["ModelResponseMapping"]
