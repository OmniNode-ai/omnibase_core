# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Ratchet verdict of the canonical-inference gate."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_canonical_inference_violation import (
    ModelCanonicalInferenceViolation,
)


class ModelCanonicalInferenceCheckOutput(BaseModel):
    """Violations split into NEW (fail the gate) and grandfathered (baselined)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    new: tuple[ModelCanonicalInferenceViolation, ...] = ()
    grandfathered: tuple[ModelCanonicalInferenceViolation, ...] = ()
