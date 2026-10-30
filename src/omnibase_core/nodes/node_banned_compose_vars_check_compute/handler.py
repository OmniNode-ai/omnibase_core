# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Banned-compose-vars check COMPUTE handler over the pure validation-layer checker."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.banned_compose_vars_check.model_banned_compose_vars_check_input import (
    ModelBannedComposeVarsCheckInput,
)
from omnibase_core.models.nodes.banned_compose_vars_check.model_banned_compose_vars_check_output import (
    ModelBannedComposeVarsCheckOutput,
)
from omnibase_core.validation.validator_banned_compose_vars import (
    find_banned_env_violations,
)


class NodeBannedComposeVarsCheckCompute:
    """Banned-compose-vars check COMPUTE handler over the pure validation-layer checker.

    Pure and deterministic: all input arrives through the typed request, so the
    handler performs no filesystem access.
    """

    def handle(
        self, request: ModelBannedComposeVarsCheckInput
    ) -> ModelBannedComposeVarsCheckOutput:
        """Run the check over the supplied request and return the result."""
        manifests = [(Path(f.path), f.source) for f in request.files]
        violations = find_banned_env_violations(manifests, frozenset(request.banned))
        return ModelBannedComposeVarsCheckOutput(violations=tuple(violations))
