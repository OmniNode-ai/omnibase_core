# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overrides: tuple[ModelConfigOverride, ...] = Field(
        default_factory=tuple,
        description="Ordered list of overrides to apply",
    )

    @property
    def by_injection_point(
        self,
    ) -> dict[EnumOverrideInjectionPoint, list[ModelConfigOverride]]:
        """Group overrides by injection point."""
        result: dict[EnumOverrideInjectionPoint, list[ModelConfigOverride]] = {}
        for override in self.overrides:
            result.setdefault(override.injection_point, []).append(override)
        return result

    def with_override(self, override: ModelConfigOverride) -> ModelConfigOverrideSet:
        """Return new set with additional override (immutable update)."""
        return ModelConfigOverrideSet(overrides=(*self.overrides, override))
