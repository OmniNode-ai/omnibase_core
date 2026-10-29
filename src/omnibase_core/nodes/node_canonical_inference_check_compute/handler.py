# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed canonical-inference ratchet partition, delegating to the validation-layer helper."""

from __future__ import annotations

from omnibase_core.models.nodes.canonical_inference_check.model_canonical_inference_check_input import (
    ModelCanonicalInferenceCheckInput,
)
from omnibase_core.models.nodes.canonical_inference_check.model_canonical_inference_check_output import (
    ModelCanonicalInferenceCheckOutput,
)
from omnibase_core.validation.validator_canonical_inference import (
    partition_against_baseline,
)


class NodeCanonicalInferenceCheckCompute:
    """Split violations into NEW and grandfathered by baseline membership."""

    def handle(
        self, request: ModelCanonicalInferenceCheckInput
    ) -> ModelCanonicalInferenceCheckOutput:
        """Return the ratchet verdict for the supplied violations."""
        new, grandfathered = partition_against_baseline(
            list(request.violations), set(request.baseline_fingerprints)
        )
        return ModelCanonicalInferenceCheckOutput(
            new=tuple(new), grandfathered=tuple(grandfathered)
        )
