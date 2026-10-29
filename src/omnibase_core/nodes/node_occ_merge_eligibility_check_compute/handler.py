# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the OCC-first merge eligibility validator."""

from __future__ import annotations

from omnibase_core.models.validation.model_occ_eligibility_input import (
    ModelOccEligibilityInput,
)
from omnibase_core.models.validation.model_occ_eligibility_result import (
    ModelOccEligibilityResult,
)
from omnibase_core.validation.validator_occ_merge_eligibility import (
    validate_occ_merge_eligibility,
)


class NodeOccMergeEligibilityCheckCompute:
    """Decide merge eligibility for one PR snapshot against a pinned OCC commit."""

    def handle(self, request: ModelOccEligibilityInput) -> ModelOccEligibilityResult:
        return validate_occ_merge_eligibility(request)
