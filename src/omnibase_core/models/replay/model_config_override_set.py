"""
Collection of configuration overrides for replay injection.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.replay.enum_override_injection_point import (
    EnumOverrideInjectionPoint,
)
from omnibase_core.models.replay.model_config_override import ModelConfigOverride

__all__ = ["ModelConfigOverrideSet"]


class ModelConfigOverrideSet(BaseModel):
    """
    A collection of configuration overrides for a replay session.

    Groups overrides by injection point for efficient batch application.

    Thread Safety:
        Immutable (frozen=True) after creation - thread-safe for concurrent reads.
    """

    # from_attributes=True: Enables construction from ORM/dataclass instances
    # and ensures pytest-xdist compatibility across worker processes where
    # class identity may differ due to independent imports.
    # See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overrides: tuple[ModelConfigOverride, ...] = Field(
        default_factory=tuple,
        description="Ordered list of overrides to apply",
    )

    @property
    def by_injection_point(
        self,
    ) -> dict[EnumOverrideInjectionPoint, list[ModelConfigOverride]]:
        """Group overrides by their injection point for efficient batch application.

        Creates a dictionary mapping each injection point to the list of overrides
        that should be applied at that point. This enables the injection service
        to process overrides in batches per injection point rather than iterating
        through all overrides for each injection point.

        Returns:
            Dict mapping EnumOverrideInjectionPoint to list of ModelConfigOverride.
            Only includes injection points that have at least one override.

        Example:
            >>> override_set = ModelConfigOverrideSet(overrides=(
            ...     ModelConfigOverride(path="a", value=1, injection_point=HANDLER_CONFIG),
            ...     ModelConfigOverride(path="b", value=2, injection_point=ENVIRONMENT),
            ...     ModelConfigOverride(path="c", value=3, injection_point=HANDLER_CONFIG),
            ... ))
            >>> grouped = override_set.by_injection_point
            >>> len(grouped[HANDLER_CONFIG])
            2
            >>> len(grouped[ENVIRONMENT])
            1
        """
        result: dict[EnumOverrideInjectionPoint, list[ModelConfigOverride]] = {}
        for override in self.overrides:
            result.setdefault(override.injection_point, []).append(override)
        return result

    def with_override(self, override: ModelConfigOverride) -> ModelConfigOverrideSet:
        """Return a new override set with an additional override appended.

        Implements immutable update pattern - creates a new instance rather than
        modifying the existing one. This is consistent with frozen=True and
        enables safe concurrent usage.

        Args:
            override: The new override to append to the set.

        Returns:
            A new ModelConfigOverrideSet with all existing overrides plus the
            new override at the end.

        Example:
            >>> original = ModelConfigOverrideSet(overrides=(override1,))
            >>> updated = original.with_override(override2)
            >>> len(original.overrides)  # Original unchanged
            1
            >>> len(updated.overrides)  # New set has both
            2
        """
        return ModelConfigOverrideSet(overrides=(*self.overrides, override))
