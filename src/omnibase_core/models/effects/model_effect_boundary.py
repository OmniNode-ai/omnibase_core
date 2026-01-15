"""Effect Boundary Model for defining effect isolation zones.

Defines boundaries where non-deterministic effects are tracked and controlled.
Part of the effect boundary system for OMN-1147.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel
from omnibase_core.models.effects.model_effect_classification import (
    ModelEffectClassification,
)

__all__ = ["ModelEffectBoundary"]


class ModelEffectBoundary(BaseModel):
    """Defines a boundary for tracking and controlling non-deterministic effects.

    An effect boundary represents a scope within which effects are classified,
    tracked, and subject to policy enforcement. Boundaries can specify isolation
    mechanisms like database snapshots for deterministic replay.

    This model is immutable after creation for thread safety.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    boundary_id: str = Field(  # string-id-ok: human-readable identifier, not UUID
        description="Unique identifier for this effect boundary",
    )
    classifications: tuple[ModelEffectClassification, ...] = Field(
        default_factory=tuple,
        description="Effect classifications within this boundary",
    )
    default_policy: EnumEffectPolicyLevel = Field(
        default=EnumEffectPolicyLevel.WARN,
        description="Default policy level for unclassified effects",
    )
    determinism_marker: bool = Field(
        default=False,
        description="Whether this boundary enforces deterministic execution",
    )
    isolation_mechanisms: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "Isolation mechanisms available in this boundary "
            "(e.g., DATABASE_READONLY_SNAPSHOT)"
        ),
    )

    def has_isolation_mechanism(self, mechanism: str) -> bool:
        """Check if a specific isolation mechanism is available."""
        return mechanism in self.isolation_mechanisms

    def has_classification_for_category(
        self,
        category: EnumEffectCategory,
    ) -> bool:
        """Check if this boundary has a classification for the given category."""
        return any(c.category == category for c in self.classifications)
