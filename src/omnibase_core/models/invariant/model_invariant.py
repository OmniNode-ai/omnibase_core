"""
Invariant model for user-defined validation rules.

Invariants are validation rules that ensure AI model changes are safe before
production deployment. Each invariant defines a specific condition that must
be satisfied for a model to be considered production-ready.
"""

import uuid

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_invariant_severity import EnumInvariantSeverity
from omnibase_core.enums.enum_invariant_type import EnumInvariantType


class ModelInvariant(BaseModel):
    """
    Base model representing a single invariant (validation rule).

    Invariants are user-defined validation rules that specify conditions
    AI models must satisfy before deployment. They can validate metrics,
    behaviors, or other properties of model outputs.

    Attributes:
        id: Unique identifier for the invariant.
        name: Human-readable name describing the invariant.
        type: Type of invariant (metric threshold, behavior check, etc.).
        severity: Severity level determining action on violation.
        config: Type-specific configuration parameters.
        enabled: Whether the invariant is currently active.
        description: Optional detailed description of the invariant.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the invariant",
    )
    name: str = Field(
        ...,
        description="Human-readable name describing the invariant",
        min_length=1,
    )
    type: EnumInvariantType = Field(
        ...,
        description="Type of invariant (metric threshold, behavior check, etc.)",
    )
    severity: EnumInvariantSeverity = Field(
        default=EnumInvariantSeverity.WARNING,
        description="Severity level determining action on violation",
    )
    config: dict[str, object] = Field(
        default_factory=dict,
        description="Type-specific configuration parameters",
    )
    enabled: bool = Field(
        default=True,
        description="Whether the invariant is currently active",
    )
    description: str | None = Field(
        default=None,
        description="Optional detailed description of the invariant",
    )


__all__ = ["ModelInvariant"]
