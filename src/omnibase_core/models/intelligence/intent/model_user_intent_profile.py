# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-user intent tendency profile model.

Captures the aggregated intent distribution and behavioral patterns for a
specific user across all their observed sessions. Used by personalization,
routing, and cost forecasting subsystems.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass

__all__ = ["ModelUserIntentProfile"]


class ModelUserIntentProfile(BaseModel):
    """Per-user intent tendency patterns.

    Aggregates observed intent distribution and resource usage patterns for
    a single user across all their tracked sessions. Enables user-personalized
    routing, quota estimation, and behavioral drift detection.

    Attributes:
        user_id: Identifier for the user (opaque string, not necessarily a UUID).
        dominant_intent_class: The intent class most frequently observed for
            this user.
        class_distribution: Mapping from intent class value (string) to
            observed fraction in [0.0, 1.0]. Values should sum to approximately
            1.0 but no strict normalization is enforced to allow partial profiles.
        avg_session_cost_usd: Average cost in US dollars per session for
            this user.
        profile_updated_at: Timestamp when this profile was last updated (UTC).
            Callers must inject this value — no ``datetime.now()`` defaults.

    Example:
        >>> from datetime import UTC, datetime
        >>> from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass
        >>> profile = ModelUserIntentProfile(
        ...     user_id="user-jonah",
        ...     dominant_intent_class=EnumIntentClass.REFACTOR,
        ...     class_distribution={
        ...         "refactor": 0.45,
        ...         "bugfix": 0.30,
        ...         "feature": 0.15,
        ...         "analysis": 0.10,
        ...     },
        ...     avg_session_cost_usd=0.042,
        ...     profile_updated_at=datetime.now(UTC),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    # string-id-ok: External user ID (auth system, CLI, etc.), not ONEX-internal UUID
    user_id: str = Field(
        description="Identifier for the user (opaque string, not necessarily a UUID)",
    )
    dominant_intent_class: EnumIntentClass = Field(
        description="The intent class most frequently observed for this user",
    )
    class_distribution: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Mapping from intent class value (string) to observed fraction in [0.0, 1.0]. "
            "Values should sum to approximately 1.0 but no strict normalization is enforced."
        ),
    )
    avg_session_cost_usd: float = Field(
        ge=0.0,
        description="Average cost in US dollars per session for this user",
    )
    profile_updated_at: datetime = Field(
        description=(
            "Timestamp when this profile was last updated (UTC). "
            "Callers must inject this value — no datetime.now() defaults."
        ),
    )

    @field_validator("class_distribution")
    @classmethod
    def validate_class_distribution(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate that all class_distribution values are in [0.0, 1.0].

        Args:
            v: The class distribution mapping to validate.

        Returns:
            The validated mapping unchanged.

        Raises:
            ValueError: If any value is outside the inclusive [0.0, 1.0] range.
        """
        invalid = {k: val for k, val in v.items() if val < 0.0 or val > 1.0}
        if invalid:
            raise ValueError(
                "class_distribution values must be within [0.0, 1.0]; "
                f"found out-of-range values: {invalid}"
            )
        return v
