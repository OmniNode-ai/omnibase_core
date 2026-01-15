"""Node Extensions Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

This module defines the ModelNodeExtensions class for storing extension data
in declarative node contracts. Extensions provide a forward-compatible mechanism
for adding new functionality without breaking existing contracts.

Stability Guarantee:
    - All fields, methods, and validators are stable interfaces
    - New optional fields may be added in minor versions only
    - Existing fields cannot be removed or have types/constraints changed
    - Breaking changes require major version bump

Extension Philosophy:
    The extensions model is intentionally minimal, configured with `extra="allow"`
    to accept arbitrary additional fields. This allows:
    - Future framework features without contract schema changes
    - Custom node-specific extensions
    - Experimental features during development

Typical Usage:
    Extensions are stored in ModelContractMeta and accessed when needed:
    - Custom handler configuration
    - Framework-specific feature flags
    - Node-specific optimization hints

Example:
    >>> extensions = ModelNodeExtensions()  # Empty extensions
    >>> # Custom extensions via model_validate
    >>> custom = ModelNodeExtensions.model_validate({"custom_handler": "my_handler"})
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelNodeExtensions(BaseModel):
    """Typed model for node extension data.

    Provides a typed, extensible container for future extension points in
    node contracts. This model is configured to allow additional fields
    (`extra="allow"`) while remaining immutable (`frozen=True`).

    The extensions model serves as a forward-compatibility mechanism:
    - New typed fields can be added in minor versions
    - Arbitrary additional fields are accepted for flexibility
    - Existing fields maintain their types and constraints

    Note:
        Currently, no typed fields are defined. Fields will be added as
        extension points are identified. Custom extensions can be passed
        via model_validate() or as keyword arguments.

    Attributes:
        (None defined yet - add typed fields as extension points are identified)

    Example:
        >>> # Create empty extensions
        >>> ext = ModelNodeExtensions()
        >>>
        >>> # Create with custom extensions (via extra="allow")
        >>> ext_custom = ModelNodeExtensions.model_validate({
        ...     "custom_handlers": ["handler1", "handler2"],
        ...     "experimental_feature": True,
        ... })
    """

    # Reserved for future extension points - add typed fields as needed
    # Example: custom_handlers: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for extensibility
        from_attributes=True,
        frozen=True,
    )


__all__ = [
    "ModelNodeExtensions",
]
