"""
Handler Specification Model.

Specification for adding handlers to contracts via patches.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1086: ModelHandlerBehavior

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.validation.validator_utils import (
    is_valid_onex_name,
    validate_import_path_format,
)

# =============================================================================
# HandlerConfigValue Type Alias
# =============================================================================
#
# Type alias for handler configuration values used in ModelHandlerSpec.config.
#
# SUPPORTED TYPES:
#   - str:        String values (URLs, addresses, identifiers)
#   - int:        Integer values (timeouts, retries, port numbers)
#   - float:      Floating-point values (thresholds, rates)
#   - bool:       Boolean flags (enable/disable features)
#   - list[str]:  String lists (server addresses, tags, allowed origins)
#   - None:       Explicit null values
#
# NOT SUPPORTED (by design):
#   - dict[str, Any] or nested dicts: Prevents deep nesting that loses type safety
#   - list[int], list[float], list[bool]: Only list[str] is supported for simplicity
#   - Complex objects (Pydantic models, dataclasses): Keep configs serializable
#   - Union types within lists: Keeps list contents homogeneous
#
# DESIGN RATIONALE:
#   This type intentionally restricts configuration values to flat, primitive types
#   to avoid the "dict[str, Any] anti-pattern" where type safety is lost in deeply
#   nested, untyped configuration structures. The restriction ensures:
#
#   1. Type Safety: All config values have known types at parse time
#   2. Serializability: Values can be safely serialized to YAML/JSON
#   3. Simplicity: Flat key-value configs are easier to validate and document
#   4. Predictability: No surprises from arbitrarily nested structures
#
#   If you need complex nested configuration, consider:
#   - Using a dedicated Pydantic model with typed fields
#   - Splitting configuration across multiple handlers
#   - Using ModelDescriptorPatch for handler behavior settings
#
# EXAMPLES:
#   Valid:
#     config={"timeout": 30}                          # int
#     config={"bootstrap_servers": "localhost:9092"}  # str
#     config={"retries": 3, "enabled": True}          # int + bool
#     config={"servers": ["host1", "host2"]}          # list[str]
#     config={"rate": 0.5, "name": None}              # float + None
#
#   Invalid (will fail type checking):
#     config={"nested": {"key": "value"}}             # Nested dict not allowed
#     config={"ports": [8080, 8081]}                  # list[int] not supported
#     config={"headers": {"Content-Type": "json"}}   # Nested dict not allowed
#
# See Also:
#   - ModelHandlerSpec: Uses this for the config field
#   - ModelDescriptorPatch: For complex handler behavior overrides
#   - ModelHandlerBehavior: Full runtime handler behavior representation
#
# .. versionadded:: 0.4.0
# =============================================================================
HandlerConfigValue = str | int | float | bool | list[str] | None

__all__ = [
    "HandlerConfigValue",
    "ModelHandlerSpec",
]


class ModelHandlerSpec(BaseModel):
    """Handler specification for adding handlers to contracts via patches.

    Handler specs provide a lightweight way to declare handlers in contract
    patches. These are resolved to full ModelHandlerBehavior instances at
    contract expansion time.

    Attributes:
        name: Handler identifier (e.g., "http_client", "kafka_producer").
        handler_type: Type of handler (e.g., "http", "kafka", "database").
        import_path: Optional Python import path for direct instantiation.
        config: Optional handler-specific configuration.

    Example:
        >>> spec = ModelHandlerSpec(
        ...     name="http_client",
        ...     handler_type="http",
        ...     import_path="mypackage.handlers.HttpClientHandler",
        ...     config={"timeout": 30, "retries": 3},
        ... )

    See Also:
        - ModelContractPatch: Uses this for handlers__add field
        - ModelHandlerBehavior: Full handler behavior model (runtime)
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(
        ...,
        min_length=1,
        description=(
            "Handler identifier (e.g., 'http_client', 'kafka_producer'). "
            "Used for handler registration and lookup. "
            "Leading/trailing whitespace is automatically stripped."
        ),
    )

    handler_type: str = Field(
        ...,
        min_length=1,
        description=(
            "Type of handler (e.g., 'http', 'kafka', 'database'). "
            "Maps to EnumHandlerType for classification. "
            "Leading/trailing whitespace is stripped and value is lowercased."
        ),
    )

    import_path: str | None = Field(
        default=None,
        description=(
            "Python import path for direct instantiation "
            "(e.g., 'mypackage.handlers.HttpClientHandler'). "
            "Leading/trailing whitespace is automatically stripped."
        ),
    )

    config: dict[str, HandlerConfigValue] | None = Field(
        default=None,
        description=(
            "Handler-specific configuration with typed values. "
            "Values are restricted to HandlerConfigValue types: str, int, float, "
            "bool, list[str], or None. Nested dicts and complex objects are NOT "
            "supported by design to maintain type safety and prevent the "
            "dict[str, Any] anti-pattern. For complex configuration needs, use "
            "dedicated Pydantic models or ModelDescriptorPatch. "
            "See HandlerConfigValue type alias documentation for full details."
        ),
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize handler name format.

        Handler names must be non-empty and contain only alphanumeric
        characters and underscores. Names are normalized to lowercase for
        consistent matching and comparison across the system. This ensures
        that 'HTTP_Client' and 'http_client' are treated as the same handler.

        Leading and trailing whitespace is stripped before validation.
        Uses shared validation utilities from omnibase_core.validation.

        Args:
            v: The raw handler name string.

        Returns:
            The validated, stripped, and lowercased handler name.

        Raises:
            ValueError: If the name is empty or contains invalid characters.
        """
        v = v.strip()
        if not v:
            raise ValueError("Handler name cannot be empty")

        # Use shared ONEX name validation (alphanumeric + underscores)
        if not is_valid_onex_name(v):
            raise ValueError(
                f"Handler name must contain only alphanumeric characters "
                f"and underscores: {v}"
            )

        # Normalize to lowercase for consistent matching
        return v.lower()

    @field_validator("handler_type")
    @classmethod
    def validate_handler_type(cls, v: str) -> str:
        """Validate handler type format.

        Handler types are normalized to lowercase and stripped of whitespace.
        They represent the transport/integration kind (e.g., 'http', 'kafka',
        'database').

        Args:
            v: The raw handler type string.

        Returns:
            The validated, stripped, and lowercased handler type.

        Raises:
            ValueError: If the handler type is empty after stripping.
        """
        v = v.strip().lower()
        if not v:
            raise ValueError("Handler type cannot be empty")

        return v

    @field_validator("import_path")
    @classmethod
    def validate_import_path(cls, v: str | None) -> str | None:
        """Validate import path format if provided.

        Import paths must be valid Python dotted paths with at least two
        components (module and class). Each module segment must be a valid
        Python identifier, and the final segment (class name) should start
        with an uppercase letter by convention.

        Uses shared validation utilities from omnibase_core.validation.
        Empty or whitespace-only strings are converted to None.

        Args:
            v: The raw import path string, or None.

        Returns:
            The validated and stripped import path, or None if empty/not provided.

        Raises:
            ValueError: If the path format is invalid.
        """
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Use shared import path validation
        is_valid, error_message = validate_import_path_format(v)
        if not is_valid:
            raise ValueError(f"{error_message}: {v}")

        return v

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (
            f"ModelHandlerSpec(name={self.name!r}, handler_type={self.handler_type!r})"
        )
