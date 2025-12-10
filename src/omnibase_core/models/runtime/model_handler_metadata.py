"""
Pydantic model for runtime validation of handler metadata.

This model provides runtime validation for handler metadata that TypedDicts
cannot enforce. Use this when you need to validate handler metadata at runtime
(e.g., during handler registration for defensive programming).

The TypedDict (TypedDictHandlerMetadata) remains the primary type for static
type checking. This model is an optional runtime validation layer.

Related:
    - OMN-226: ProtocolHandler protocol
    - TypedDictHandlerMetadata: Static type definition (no runtime validation)

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHandlerMetadata(BaseModel):
    """Runtime-validated handler metadata.

    This Pydantic model validates handler metadata at runtime, catching issues
    that TypedDicts cannot detect (missing required fields, wrong types, etc.).

    Usage:
        .. code-block:: python

            from omnibase_core.models.runtime import ModelHandlerMetadata

            # Validate metadata at runtime
            raw_metadata = handler.describe()
            validated = ModelHandlerMetadata.model_validate(raw_metadata)

            # Access validated fields
            print(f"Handler: {validated.name} v{validated.version}")

    Attributes:
        name: Human-readable handler name (e.g., "http_handler").
        version: Handler version as ModelSemVer.
        description: Brief description of the handler's purpose (optional).
        capabilities: List of supported operations/features (optional).

    Example:
        >>> metadata = ModelHandlerMetadata(
        ...     name="http_handler",
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     description="Handles HTTP requests",
        ... )
        >>> metadata.name
        'http_handler'
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        extra="forbid",
    )

    name: str = Field(..., description="Human-readable handler name")
    version: ModelSemVer = Field(..., description="Handler version as ModelSemVer")
    description: str | None = Field(
        default=None, description="Brief description of the handler's purpose"
    )
    capabilities: list[str] | None = Field(
        default=None, description="List of supported operations/features"
    )


__all__ = ["ModelHandlerMetadata"]
