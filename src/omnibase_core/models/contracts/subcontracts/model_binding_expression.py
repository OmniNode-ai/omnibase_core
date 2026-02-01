"""Binding expression model for operation bindings DSL.

Validates and parses expression strings in the format:
- `${root.path}` - simple path access
- `${root.path | function}` - path with pipe function

Allowed roots: binding.config, contract.config, request, result
Allowed functions: to_json, from_json (no chaining)

VERSION: 1.0.0

Author: ONEX Framework Team
"""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, PrivateAttr, field_validator

from omnibase_core.constants.constants_effect import contains_denied_builtin
from omnibase_core.enums.enum_binding_function import EnumBindingFunction
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelBindingExpression(BaseModel):
    """
    Binding expression for operation bindings DSL.

    Validates and parses expression strings like `${request.snapshot | to_json}`.
    This is intentionally a "dumb DSL" with strict limitations:

    - Only 4 allowed roots: binding.config, contract.config, request, result
    - Only dot-path access (no brackets, ternary, math)
    - Only 2 pipe functions: to_json, from_json
    - No function chaining (only one pipe allowed)

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.

    Security:
        Path segments are validated against DENIED_BUILTINS to prevent
        template injection attacks (e.g., __class__, __import__, eval).

    Examples:
        >>> expr = ModelBindingExpression(raw="${request.snapshot}")
        >>> expr.root
        'request'
        >>> expr.path
        'snapshot'
        >>> expr.function
        None

        >>> expr = ModelBindingExpression(raw="${result.data | to_json}")
        >>> expr.function
        <EnumBindingFunction.TO_JSON: 'to_json'>
    """

    # Expression pattern: ${root.path} or ${root.path | function}
    # Groups: root, path (optional), function (optional)
    EXPRESSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^\$\{(?P<root>binding\.config|contract\.config|request|result)"
        r"(?:\.(?P<path>[a-zA-Z_][a-zA-Z0-9_.]*))?"
        r"(?:\s*\|\s*(?P<function>to_json|from_json))?\}$"
    )

    # Allowed root prefixes for expressions
    ALLOWED_ROOTS: ClassVar[frozenset[str]] = frozenset(
        {"binding.config", "contract.config", "request", "result"}
    )

    raw: str
    """The raw expression string (e.g., '${request.snapshot | to_json}')."""

    # Internal parsed components (set during __init__ after validation)
    _root: str = PrivateAttr(default="")
    _path: str | None = PrivateAttr(default=None)
    _function: EnumBindingFunction | None = PrivateAttr(default=None)

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("raw", mode="before")
    @classmethod
    def validate_and_parse_expression(cls, value: object) -> str:
        """
        Validate and parse the binding expression.

        This validator ensures the expression follows the DSL format and
        contains no security-sensitive patterns.

        Args:
            value: The raw expression string to validate.

        Returns:
            The validated raw expression string.

        Raises:
            ModelOnexError: If the expression is invalid or contains
                security-sensitive patterns.
        """
        if not isinstance(value, str):
            raise ModelOnexError(
                message=f"Binding expression must be a string, got {type(value).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if not value:
            raise ModelOnexError(
                message="Binding expression cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Check for chained pipes (more than one |)
        pipe_count = value.count("|")
        if pipe_count > 1:
            raise ModelOnexError(
                message=f"Chained pipes not allowed in binding expression: {value!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                expression=value,
                pipe_count=pipe_count,
            )

        # Match against the expression pattern
        match = cls.EXPRESSION_PATTERN.match(value)
        if not match:
            # Provide helpful error message for common mistakes
            if value.startswith("${config."):
                raise ModelOnexError(
                    message=(
                        f"Ambiguous root 'config' in expression: {value!r}. "
                        "Use 'binding.config' for local config or 'contract.config' for contract config."
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    expression=value,
                )
            if "?" in value or ":" in value:
                raise ModelOnexError(
                    message=f"Ternary operators not allowed in binding expression: {value!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    expression=value,
                )
            if "[" in value or "]" in value:
                raise ModelOnexError(
                    message=f"Bracket notation not allowed in binding expression: {value!r}. Use dot-path only.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    expression=value,
                )

            raise ModelOnexError(
                message=f"Invalid binding expression format: {value!r}. Expected format: ${{root.path}} or ${{root.path | function}}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                expression=value,
                allowed_roots=list(cls.ALLOWED_ROOTS),
                allowed_functions=["to_json", "from_json"],
            )

        # Extract and validate path for security
        path = match.group("path")
        if path:
            # Check for denied builtins in the path
            denied = contains_denied_builtin(path)
            if denied:
                raise ModelOnexError(
                    message=f"Security violation: forbidden identifier '{denied}' in binding expression path: {value!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    expression=value,
                    denied_builtin=denied,
                )

            # Additional security check: no double underscores anywhere in path
            if "__" in path:
                raise ModelOnexError(
                    message=f"Security violation: double underscore not allowed in binding expression path: {value!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    expression=value,
                    path=path,
                )

        return value

    def __init__(self, **data: object) -> None:
        """Initialize and parse the binding expression."""
        super().__init__(**data)

        # Parse components after validation.
        # NOTE: This regex match is intentionally separate from the validator's match.
        # Validation and construction are decoupled concerns - the validator ensures
        # correctness and provides detailed error messages, while __init__ extracts
        # the parsed components. This separation allows for future optimizations
        # (e.g., caching) without coupling validation logic to construction.
        match = self.EXPRESSION_PATTERN.match(self.raw)
        if match:
            # Use object.__setattr__ because model is frozen
            object.__setattr__(self, "_root", match.group("root"))
            object.__setattr__(self, "_path", match.group("path"))
            func_str = match.group("function")
            if func_str:
                object.__setattr__(self, "_function", EnumBindingFunction(func_str))

    @property
    def root(self) -> str:
        """
        The root of the expression.

        Returns:
            One of: 'binding.config', 'contract.config', 'request', 'result'
        """
        return self._root

    @property
    def path(self) -> str | None:
        """
        The dot-path after the root.

        Returns:
            The path string (e.g., 'snapshot.id') or None if no path.
        """
        return self._path

    @property
    def function(self) -> EnumBindingFunction | None:
        """
        The pipe function if specified.

        Returns:
            EnumBindingFunction.TO_JSON, EnumBindingFunction.FROM_JSON, or None.
        """
        return self._function

    @property
    def full_path(self) -> str:
        """
        The complete path including root.

        Returns:
            Full path like 'request.snapshot.id' or 'binding.config.base_path'.
        """
        if self._path:
            return f"{self._root}.{self._path}"
        return self._root

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return f"ModelBindingExpression(raw={self.raw!r})"

    def __str__(self) -> str:
        """Return the raw expression string."""
        return self.raw


__all__ = ["ModelBindingExpression"]
