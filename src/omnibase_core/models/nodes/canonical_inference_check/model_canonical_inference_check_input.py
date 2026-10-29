# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Scanned violations and the grandfathering baseline for the canonical-inference ratchet."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_canonical_inference_violation import (
    ModelCanonicalInferenceViolation,
)


class ModelCanonicalInferenceCheckInput(BaseModel):
    """Violations found by the scan and the baseline fingerprints that grandfather them."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: tuple[ModelCanonicalInferenceViolation, ...] = ()
    baseline_fingerprints: frozenset[str] = frozenset()
