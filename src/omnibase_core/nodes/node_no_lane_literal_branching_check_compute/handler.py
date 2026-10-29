# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""NodeNoLaneLiteralBranchingCheckCompute — lane-literal branching COMPUTE handler.

Pure and deterministic: source text arrives on the request; the filesystem walk,
baseline handling and printing happen in the runtime, never here. The scanner
lives in ``omnibase_core.validation.validator_no_lane_literal_branching``.

Ticket: OMN-21520.
"""

from __future__ import annotations

from omnibase_core.models.nodes.no_lane_literal_branching_check.model_no_lane_literal_branching_check_input import (
    ModelNoLaneLiteralBranchingCheckInput,
)
from omnibase_core.models.nodes.no_lane_literal_branching_check.model_no_lane_literal_branching_check_output import (
    ModelNoLaneLiteralBranchingCheckOutput,
)
from omnibase_core.validation.validator_no_lane_literal_branching import scan_source

__all__ = ["NodeNoLaneLiteralBranchingCheckCompute"]


class NodeNoLaneLiteralBranchingCheckCompute:
    """COMPUTE handler that scans (path, source) pairs for lane-name branching."""

    def handle(
        self, request: ModelNoLaneLiteralBranchingCheckInput
    ) -> ModelNoLaneLiteralBranchingCheckOutput:
        """Return every lane-literal branching finding in the supplied files."""
        return ModelNoLaneLiteralBranchingCheckOutput(
            violations=tuple(
                violation
                for file in request.files
                for violation in scan_source(file.source, path=file.path)
            )
        )
