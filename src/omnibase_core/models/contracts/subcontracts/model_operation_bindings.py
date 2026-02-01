"""Operation bindings subcontract model.

Top-level subcontract for the operation bindings DSL. Wires operations to a
handler declaratively, replacing the need for code adapters.

This subcontract enables contract-driven handler binding where:
- A single handler class processes all operations
- Each operation is mapped to a specific envelope template and response mapping
- Configuration can use expressions referencing contract or binding config

Example YAML contract configuration:
    operation_bindings:
      version:
        major: 1
        minor: 0
        patch: 0
      handler: "omnibase_infra.handlers.handler_filesystem.HandlerFileSystem"
      config:
        base_path: "${contract.config.base_path}"
        allowed_paths: ["${contract.config.base_path}"]

      mappings:
        store:
          envelope:
            operation: "write_file"
            path: "${binding.config.base_path}/snapshots/${request.snapshot.snapshot_id}.json"
            content: "${request.snapshot | to_json}"
          response:
            status: "${result.status}"
            snapshot: "${request.snapshot}"

Documentation:
    For complete DSL syntax, validation rules, and examples, see:
    docs/contracts/OPERATION_BINDINGS_DSL.md

VERSION: 1.0.0

Author: ONEX Framework Team
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants.constants_effect import DENIED_BUILTINS
from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.subcontracts.model_operation_mapping import (
    ModelOperationMapping,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


@allow_dict_any(
    reason="Config field intentionally accepts arbitrary nested values for DSL "
    "flexibility. Config values may contain ${...} expressions referencing "
    "contract.config or binding.config, validated at runtime."
)
class ModelOperationBindings(BaseModel):
    """
    Operation bindings subcontract for declarative handler wiring.

    This subcontract enables contract-driven binding of operations to handlers,
    eliminating the need for code adapters. The handler class is specified by
    its Python import path and configured with expressions that reference
    contract or binding configuration.

    Handler Path Format:
        The handler field must be a valid Python dotted import path:
        - Must contain at least one dot (e.g., "module.Handler")
        - Must not contain double underscores (security)
        - Each segment must be a valid Python identifier

    Config Expressions:
        Config values can be:
        - Literal values (strings, numbers, lists, dicts)
        - Expression strings using ${...} syntax for dynamic values

    Example YAML:
        operation_bindings:
          version:
            major: 1
            minor: 0
            patch: 0
          handler: "omnibase_infra.handlers.handler_filesystem.HandlerFileSystem"
          config:
            base_path: "${contract.config.base_path}"
          mappings:
            store:
              envelope:
                operation: "write_file"
                path: "${binding.config.base_path}/${request.id}.json"
              response:
                status: "${result.status}"

    Example usage:
        >>> bindings = ModelOperationBindings(
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     handler="mymodule.handlers.MyHandler",
        ...     mappings={
        ...         "process": ModelOperationMapping(
        ...             envelope=ModelEnvelopeTemplate(operation="do_work"),
        ...             response=ModelResponseMapping(result="${result.data}")
        ...         )
        ...     }
        ... )
        >>> bindings.handler
        'mymodule.handlers.MyHandler'
    """

    # Pattern for valid Python dotted import path
    # Must have at least one dot, each segment must be valid Python identifier
    HANDLER_PATH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$"
    )

    # Pattern to detect expression strings that need validation
    EXPRESSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\$\{[^}]+\}")

    # Valid expression roots for config values
    ALLOWED_CONFIG_ROOTS: ClassVar[frozenset[str]] = frozenset(
        {"binding.config", "contract.config"}
    )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        validate_assignment=True,
    )

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    version: ModelSemVer = Field(
        ...,  # REQUIRED - must be provided in YAML contract
        description="Subcontract version (MUST be provided in YAML contract)",
    )

    handler: str = Field(
        ...,  # REQUIRED
        description=(
            "Python dotted import path to the handler class. "
            "Format: 'module.submodule.ClassName'. "
            "The handler is NOT imported at validation time - only path format is checked."
        ),
    )

    config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Local configuration for this binding. Values can be literals or "
            "expression strings using ${binding.config.x} or ${contract.config.x} syntax."
        ),
    )

    mappings: dict[str, ModelOperationMapping] = Field(
        ...,  # REQUIRED
        description=(
            "Mapping of operation names to their envelope/response definitions. "
            "Keys are operation names (e.g., 'store', 'retrieve'), values are "
            "ModelOperationMapping instances defining how to construct envelopes "
            "and map responses."
        ),
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of this operation binding",
    )

    @field_validator("handler", mode="before")
    @classmethod
    def validate_handler_path(cls, value: object) -> str:
        """
        Validate handler path is a valid Python dotted import path.

        This validation checks FORMAT only - the handler is NOT imported.
        Runtime resolution is handled separately by the execution layer.

        Raises:
            ModelOnexError: If handler path format is invalid.
        """
        if not isinstance(value, str):
            raise ModelOnexError(
                message=f"Handler must be a string, got {type(value).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="handler",
                value=value,
            )

        if not value:
            raise ModelOnexError(
                message="Handler path cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="handler",
                value=value,
            )

        # Security: no double underscores (prevents __import__, __class__, etc.)
        if "__" in value:
            raise ModelOnexError(
                message=f"Handler path cannot contain double underscores (security): {value!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="handler",
                value=value,
                constraint="no_double_underscore",
            )

        # Must match Python dotted path pattern (at least one dot)
        if not cls.HANDLER_PATH_PATTERN.match(value):
            raise ModelOnexError(
                message=(
                    f"Invalid handler path format: {value!r}. "
                    "Expected Python dotted import path with at least one dot "
                    "(e.g., 'module.ClassName' or 'package.module.ClassName')."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="handler",
                value=value,
                constraint="dotted_import_path",
            )

        return value

    @model_validator(mode="after")
    def validate_operation_bindings(self) -> ModelOperationBindings:
        """
        Validate operation bindings after model construction.

        Validates:
        - At least one mapping is defined
        - Config expressions use only allowed roots (binding.config, contract.config)
        - Config expressions do not contain denied builtins

        Raises:
            ModelOnexError: If validation fails.
        """
        # Validate at least one mapping exists
        if not self.mappings:
            raise ModelOnexError(
                message="Operation bindings must have at least one mapping defined",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="mappings",
                value=None,
                constraint="non_empty_mappings",
            )

        # Validate config expressions if present
        if self.config:
            self._validate_config_expressions(self.config)

        return self

    def _validate_config_expressions(
        self, config: dict[str, Any], path_prefix: str = "config"
    ) -> None:
        """
        Recursively validate expressions in config values.

        Config values can be:
        - Literals (pass through)
        - Expression strings (must use allowed roots, no denied builtins)
        - Nested dicts/lists (recurse)

        Args:
            config: The config dict to validate.
            path_prefix: Current path for error context.

        Raises:
            ModelOnexError: If an expression is invalid.
        """
        for key, value in config.items():
            field_path = f"{path_prefix}.{key}"

            if isinstance(value, str):
                self._validate_expression_string(value, field_path)
            elif isinstance(value, dict):
                self._validate_config_expressions(value, field_path)
            elif isinstance(value, list):
                self._validate_list_items(value, field_path)
            # Literals (int, float, bool, None) pass through without validation

    def _validate_list_items(self, items: list[Any], path_prefix: str) -> None:
        """
        Recursively validate list items for expressions.

        Handles nested lists by recursing into them.

        Args:
            items: The list to validate.
            path_prefix: Current path for error context.

        Raises:
            ModelOnexError: If an expression is invalid.
        """
        for i, item in enumerate(items):
            item_path = f"{path_prefix}[{i}]"
            if isinstance(item, str):
                self._validate_expression_string(item, item_path)
            elif isinstance(item, dict):
                self._validate_config_expressions(item, item_path)
            elif isinstance(item, list):
                self._validate_list_items(item, item_path)
            # Literals (int, float, bool, None) pass through without validation

    # Allowed pipe functions for config expressions
    ALLOWED_PIPE_FUNCTIONS: ClassVar[frozenset[str]] = frozenset(
        {"to_json", "from_json"}
    )

    def _validate_expression_string(self, value: str, field_path: str) -> None:
        """
        Validate a string value that may contain expressions.

        If the string contains ${...}, validate it follows the allowed format.
        Strings without expressions are treated as literals.

        Validation rules:
        - No empty expressions
        - No ternary operators (? and :)
        - No bracket notation ([ or ])
        - No chained pipes (more than one |)
        - Pipe functions must be in whitelist (to_json, from_json)
        - No double underscores (security)
        - No denied builtins
        - Root must be exactly 'binding.config' or 'contract.config'

        Args:
            value: The string value to validate.
            field_path: Current path for error context.

        Raises:
            ModelOnexError: If expression format is invalid.
        """
        # Find all expressions in the string
        expressions = self.EXPRESSION_PATTERN.findall(value)
        if not expressions:
            return  # No expressions, treat as literal

        for expr in expressions:
            # Extract the content inside ${...}
            inner = expr[2:-1].strip()  # Remove ${ and }

            # Check for empty expression
            if not inner:
                raise ModelOnexError(
                    message=f"Empty expression not allowed: {expr!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    field=field_path,
                    value=value,
                    expression=expr,
                    constraint="non_empty_expression",
                )

            # Reject ternary operators
            if "?" in inner and ":" in inner:
                raise ModelOnexError(
                    message=f"Ternary operators not allowed in config: {expr!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    field=field_path,
                    value=value,
                    expression=expr,
                    constraint="no_ternary_operators",
                )

            # Reject bracket notation
            if "[" in inner or "]" in inner:
                raise ModelOnexError(
                    message=f"Bracket notation not allowed in config: {expr!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    field=field_path,
                    value=value,
                    expression=expr,
                    constraint="no_bracket_notation",
                )

            # Check for chained pipes
            if inner.count("|") > 1:
                raise ModelOnexError(
                    message=f"Chained pipes not allowed in config: {expr!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    field=field_path,
                    value=value,
                    expression=expr,
                    constraint="no_chained_pipes",
                )

            # Split on pipe
            parts = inner.split("|")
            path_part = parts[0].strip()
            func_part = parts[1].strip() if len(parts) > 1 else None

            # Validate pipe function if present
            if func_part is not None and func_part not in self.ALLOWED_PIPE_FUNCTIONS:
                raise ModelOnexError(
                    message=f"Invalid pipe function in config: {func_part!r}. Allowed: to_json, from_json",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    field=field_path,
                    value=value,
                    expression=expr,
                    constraint="allowed_pipe_functions",
                    allowed_functions=list(self.ALLOWED_PIPE_FUNCTIONS),
                )

            # Security: no double underscores
            if "__" in inner:
                raise ModelOnexError(
                    message=f"Expression cannot contain double underscores (security): {expr!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    field=field_path,
                    value=value,
                    expression=expr,
                    constraint="no_double_underscore",
                )

            # Check for denied builtins in path segments
            for segment in path_part.split("."):
                if segment in DENIED_BUILTINS:
                    raise ModelOnexError(
                        message=f"Security violation: forbidden identifier '{segment}' in expression: {expr!r}",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        field=field_path,
                        value=value,
                        expression=expr,
                        denied_builtin=segment,
                    )

            # Validate root is allowed for config (exact match required)
            # Must be exactly 'binding.config' or 'contract.config' or start with those + '.'
            root_valid = False
            for allowed_root in self.ALLOWED_CONFIG_ROOTS:
                if path_part == allowed_root or path_part.startswith(
                    f"{allowed_root}."
                ):
                    root_valid = True
                    break

            if not root_valid:
                raise ModelOnexError(
                    message=(
                        f"Config expression must use 'binding.config' or 'contract.config' root: {expr!r}. "
                        f"Got root from path: {path_part!r}"
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    field=field_path,
                    value=value,
                    expression=expr,
                    constraint="allowed_config_roots",
                    allowed_roots=list(self.ALLOWED_CONFIG_ROOTS),
                )

    def get_all_operation_names(self) -> set[str]:
        """
        Get all operation names defined in this binding.

        Returns:
            Set of operation names from the mappings dict.

        Example:
            >>> bindings = ModelOperationBindings(...)
            >>> bindings.get_all_operation_names()
            {'store', 'retrieve', 'delete'}
        """
        return set(self.mappings.keys())

    def get_mapping(self, operation: str) -> ModelOperationMapping | None:
        """
        Get the mapping for a specific operation.

        Args:
            operation: The operation name to look up.

        Returns:
            The ModelOperationMapping for the operation, or None if not found.
        """
        return self.mappings.get(operation)

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        ops = list(self.mappings.keys())
        return f"ModelOperationBindings(handler={self.handler!r}, operations={ops})"


__all__ = ["ModelOperationBindings"]
