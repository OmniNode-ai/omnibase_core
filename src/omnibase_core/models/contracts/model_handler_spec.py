# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Specification Model.

Specification for adding handlers to contracts via patches.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1086: ModelHandlerDescriptor

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Type alias for handler config values - supports common primitive types
# without the full dict[str, Any] anti-pattern
HandlerConfigValue = str | int | float | bool | list[str] | None

__all__ = [
    "ModelHandlerSpec",
]


class ModelHandlerSpec(BaseModel):
    """Handler specification for adding handlers to contracts via patches.

    Handler specs provide a lightweight way to declare handlers in contract
    patches. These are resolved to full ModelHandlerDescriptor instances at
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
        - ModelHandlerDescriptor: Full handler descriptor model (OMN-1086)
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(
        ...,
        min_length=1,
        description=(
            "Handler identifier (e.g., 'http_client', 'kafka_producer'). "
            "Used for handler registration and lookup."
        ),
    )

    handler_type: str = Field(
        ...,
        min_length=1,
        description=(
            "Type of handler (e.g., 'http', 'kafka', 'database'). "
            "Maps to EnumHandlerType for classification."
        ),
    )

    import_path: str | None = Field(
        default=None,
        description=(
            "Python import path for direct instantiation "
            "(e.g., 'mypackage.handlers.HttpClientHandler')."
        ),
    )

    config: dict[str, HandlerConfigValue] | None = Field(
        default=None,
        description="Handler-specific configuration with typed values.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate handler name format."""
        v = v.strip()
        if not v:
            raise ValueError("Handler name cannot be empty")

        # Handler names should be lowercase with underscores
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError(
                f"Handler name must contain only alphanumeric characters "
                f"and underscores: {v}"
            )

        return v

    @field_validator("handler_type")
    @classmethod
    def validate_handler_type(cls, v: str) -> str:
        """Validate handler type format."""
        v = v.strip().lower()
        if not v:
            raise ValueError("Handler type cannot be empty")

        return v

    @field_validator("import_path")
    @classmethod
    def validate_import_path(cls, v: str | None) -> str | None:
        """Validate import path format if provided."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Basic validation - should be valid Python import path
        parts = v.split(".")
        if len(parts) < 2:
            raise ValueError(f"Import path must include module and class: {v}")

        return v

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (
            f"ModelHandlerSpec(name={self.name!r}, handler_type={self.handler_type!r})"
        )
