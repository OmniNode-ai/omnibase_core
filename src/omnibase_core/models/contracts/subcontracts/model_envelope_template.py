"""Envelope template model for operation bindings DSL.

Defines how to construct handler envelopes from request data using
templated fields with ${...} expression placeholders.

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
    reason="Template fields intentionally accept arbitrary nested values (str, int, "
    "float, bool, list, dict) for DSL flexibility. String values may contain ${...} "
    "expressions that are validated at runtime."
)
class ModelEnvelopeTemplate(BaseModel):
    """
    Envelope template for constructing handler envelopes from request data.

    This model defines the structure of an envelope that will be passed to
    a handler, with support for templated values using ${...} expressions.

    Template values can be:
        - str: May contain ${...} expressions for dynamic substitution
        - int, float, bool: Literal values passed through unchanged
        - list[TemplateValue]: Recursive list of template values
        - dict[str, TemplateValue]: Recursive dict of template values

    Expression Format:
        Expressions follow the ModelBindingExpression format:
        - ${root.path} - simple path access
        - ${root.path | function} - path with pipe function

        Allowed roots: binding.config, contract.config, request, result
        Allowed functions: to_json, from_json

    Example:
        >>> template = ModelEnvelopeTemplate(
        ...     operation="write_file",
        ...     fields={
        ...         "path": "${binding.config.base_path}/snapshots/${request.snapshot.snapshot_id}.json",
        ...         "content": "${request.snapshot | to_json}",
        ...         "mode": "w",
        ...         "encoding": "utf-8",
        ...     }
        ... )

    YAML Contract Example:
        .. code-block:: yaml

            envelope:
              operation: "write_file"
              path: "${binding.config.base_path}/snapshots/${request.snapshot.snapshot_id}.json"
              content: "${request.snapshot | to_json}"

    See Also:
        - ModelBindingExpression: Expression validation and parsing
        - ModelHandlerRoutingEntry: Uses envelope templates for handler routing
    """

    # Expression pattern for basic validation
    # This is a simplified pattern to check if a string looks like it could
    # contain valid expressions. Full validation happens in ModelBindingExpression.
    EXPRESSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\$\{(?P<content>[^}]+)\}"
    )

    # Pattern to detect empty ${} expressions (user error that should be rejected)
    EMPTY_EXPRESSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\$\{\}")

    # Allowed roots for expressions (must match ModelBindingExpression.ALLOWED_ROOTS)
    ALLOWED_ROOTS: ClassVar[frozenset[str]] = frozenset(
        {"binding.config", "contract.config", "request", "result"}
    )

    # Allowed pipe functions (must match ModelBindingExpression)
    ALLOWED_FUNCTIONS: ClassVar[frozenset[str]] = frozenset({"to_json", "from_json"})

    # Maximum recursion depth for nested validation (matches ModelResponseMapping)
    MAX_RECURSION_DEPTH: ClassVar[int] = 20

    operation: str = Field(
        ...,
        description="The operation name (e.g., 'write_file', 'read_file', 'http_request')",
        min_length=1,
    )

    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional fields for the envelope where values can contain ${...} expressions",
    )

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

    def _validate_value(self, value: Any, path: str = "", depth: int = 0) -> None:
        """
        Recursively validate template values for valid expressions.

        Args:
            value: The value to validate (may be str, dict, list, or literal).
            path: The current path for error messages.
            depth: Current recursion depth to prevent DoS via deeply nested structures.

        Raises:
            ValueError: If a string contains an invalid ${...} expression,
                or if maximum nesting depth is exceeded.
        """
        if depth > self.MAX_RECURSION_DEPTH:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Maximum nesting depth ({self.MAX_RECURSION_DEPTH}) exceeded at {path!r}"
            )

        if isinstance(value, str) and "${" in value:
            self._validate_expressions_in_string(value, path)
        elif isinstance(value, dict):
            for key, val in value.items():
                self._validate_value(
                    val, path=f"{path}.{key}" if path else key, depth=depth + 1
                )
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                self._validate_value(item, path=f"{path}[{idx}]", depth=depth + 1)

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
        # Check for empty ${} expressions first (these don't match EXPRESSION_PATTERN)
        if self.EMPTY_EXPRESSION_PATTERN.search(value):
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Empty expression '${{}}' is not allowed at {path!r}. "
                f"Use a valid expression like '${{request.field}}' in {value!r}"
            )

        for match in self.EXPRESSION_PATTERN.finditer(value):
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

        # Check for security-sensitive patterns
        if "__" in path_part:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Security violation at {path!r}: "
                f"double underscore not allowed in expression path: {path_part!r}"
            )

        # Check for denied builtins (eval, exec, __class__, etc.)
        denied = contains_denied_builtin(path_part)
        if denied:
            # error-ok: Pydantic validator requires ValueError for conversion to ValidationError
            raise ValueError(
                f"Security violation at {path!r}: "
                f"forbidden identifier '{denied}' in expression path: {path_part!r}"
            )


__all__ = ["ModelEnvelopeTemplate"]
