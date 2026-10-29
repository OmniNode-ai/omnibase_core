# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Banned-environment-variable drift violations found in the supplied manifests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_compose_drift_violation import (
    ModelComposeDriftViolation,
)


class ModelBannedComposeVarsCheckOutput(BaseModel):
    """Banned-environment-variable drift violations found in the supplied manifests."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: tuple[ModelComposeDriftViolation, ...] = Field(default_factory=tuple)
