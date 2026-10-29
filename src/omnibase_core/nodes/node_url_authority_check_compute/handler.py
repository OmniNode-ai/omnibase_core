# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the url-authority scanner (OMN-21520)."""

from __future__ import annotations

from omnibase_core.models.nodes.url_authority_check.model_url_authority_check_input import (
    ModelUrlAuthorityCheckInput,
)
from omnibase_core.models.nodes.url_authority_check.model_url_authority_check_output import (
    ModelUrlAuthorityCheckOutput,
)
from omnibase_core.models.validation.model_url_authority_violation import (
    ModelUrlAuthorityViolation,
)
from omnibase_core.validation.validator_url_authority import scan_source


class NodeUrlAuthorityCheckCompute:
    """Scan inline (path, source) pairs and return every url-authority violation."""

    def handle(
        self, request: ModelUrlAuthorityCheckInput
    ) -> ModelUrlAuthorityCheckOutput:
        """Delegate to the validation-layer scanner, file by file, in input order."""
        violations: list[ModelUrlAuthorityViolation] = []
        for file in request.files:
            violations.extend(scan_source(request.repo, file.path, file.source))
        return ModelUrlAuthorityCheckOutput(violations=tuple(violations))
