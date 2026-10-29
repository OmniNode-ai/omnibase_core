# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""File naming convention check COMPUTE handler over the pure validation-layer checker."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.naming_convention_check.model_naming_convention_check_input import (
    ModelNamingConventionCheckInput,
)
from omnibase_core.models.nodes.naming_convention_check.model_naming_convention_check_output import (
    ModelNamingConventionCheckOutput,
)
from omnibase_core.validation.checker_naming_convention import check_file_name


class NodeNamingConventionCheckCompute:
    """File naming convention check COMPUTE handler over the pure validation-layer checker.

    Pure and deterministic: all input arrives through the typed request, so the
    handler performs no filesystem access.
    """

    def handle(
        self, request: ModelNamingConventionCheckInput
    ) -> ModelNamingConventionCheckOutput:
        """Run the check over the supplied request and return the result."""
        errors: list[str] = []
        for path in request.paths:
            error = check_file_name(Path(path))
            if error:
                errors.append(f"{path}: {error}")
        return ModelNamingConventionCheckOutput(errors=tuple(errors))
