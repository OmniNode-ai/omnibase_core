"""Effect Classification Model for categorizing non-deterministic effects.

Provides structured classification of effects for replay safety analysis.
Part of the effect boundary system for OMN-1147.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_effect_category import EnumEffectCategory

__all__ = ["ModelEffectClassification"]


class ModelEffectClassification(BaseModel):
    """Classification of a non-deterministic effect for replay safety.

    Captures metadata about an effect's category, determinism characteristics,
    and associated risks during replay. Used by the effect boundary system
    to make policy decisions about effect execution.

    This model is immutable after creation for thread safety and use as
    dictionary keys in effect registries.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    category: EnumEffectCategory = Field(
        description="The category of non-deterministic effect",
    )
    description: str = Field(
        description="Human-readable description of the effect",
    )
    nondeterministic: bool = Field(
        default=True,
        description="Whether this effect produces non-deterministic results",
    )
    replay_risk_notes: str | None = Field(
        default=None,
        description="Notes about specific risks when replaying this effect",
    )
    tags: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Additional tags for effect filtering and grouping",
    )
