"""
Node Extensions Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed
- Breaking changes require major version bump

This module defines the extension model for declarative node contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelNodeExtensions(BaseModel):
    """Typed model for node extension data.

    Provides structured typed fields for extension data (replaces untyped dict).
    Add new extension fields here as needed.
    """

    # Reserved for future extension points - add typed fields as needed
    # Example: custom_handlers: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for extensibility
        frozen=True,
    )


__all__ = [
    "ModelNodeExtensions",
]
