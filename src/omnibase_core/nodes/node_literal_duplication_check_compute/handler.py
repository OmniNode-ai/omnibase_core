# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Literal-duplication check COMPUTE handler over the pure validation-layer checker."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.literal_duplication_check.model_literal_duplication_check_input import (
    ModelLiteralDuplicationCheckInput,
)
from omnibase_core.models.nodes.literal_duplication_check.model_literal_duplication_check_output import (
    ModelLiteralDuplicationCheckOutput,
)
from omnibase_core.validation.checker_literal_duplication import (
    KNOWN_ENUM_NAMES,
    validate_source,
)


class NodeLiteralDuplicationCheckCompute:
    """Literal-duplication check COMPUTE handler over the pure validation-layer checker.

    Pure and deterministic: all input arrives through the typed request, so the
    handler performs no filesystem access.
    """

    def handle(
        self, request: ModelLiteralDuplicationCheckInput
    ) -> ModelLiteralDuplicationCheckOutput:
        """Run the check over the supplied request and return the result."""
        known_enums = (
            frozenset(request.known_enums) if request.known_enums else KNOWN_ENUM_NAMES
        )
        errors: list[str] = []
        for source_file in request.files:
            errors.extend(
                validate_source(source_file.source, Path(source_file.path), known_enums)
            )
        return ModelLiteralDuplicationCheckOutput(errors=tuple(errors))
