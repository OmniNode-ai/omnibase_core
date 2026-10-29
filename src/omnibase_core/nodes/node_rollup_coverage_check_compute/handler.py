# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the Model-B rollup-coverage verifier (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.rollup_coverage_check.model_rollup_coverage_check_input import (
    ModelRollupCoverageCheckInput,
)
from omnibase_core.models.nodes.rollup_coverage_check.model_rollup_coverage_check_output import (
    ModelRollupCoverageCheckOutput,
)
from omnibase_core.validation.validator_rollup_coverage import RollupCoverageVerifier


class NodeRollupCoverageCheckCompute:
    """Verify one repo's rollup coverage and return opt-in state with its gaps."""

    def handle(
        self, request: ModelRollupCoverageCheckInput
    ) -> ModelRollupCoverageCheckOutput:
        """Delegate to the validation-layer verifier; the canonical spec is the default."""
        verifier = (
            RollupCoverageVerifier.from_spec_path(Path(request.spec_path))
            if request.spec_path is not None
            else RollupCoverageVerifier.from_canonical()
        )
        if not verifier.is_opted_in(request.repo):
            return ModelRollupCoverageCheckOutput(opted_in=False)
        gaps = verifier.verify_repo(
            repo_name=request.repo, repo_root=Path(request.repo_root)
        )
        return ModelRollupCoverageCheckOutput(opted_in=True, gaps=tuple(gaps))
