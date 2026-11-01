# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Thin COMPUTE shell for invariant analysis; the logic lives in the handler (OMN-21565)."""

from __future__ import annotations

from typing import cast

from omnibase_core.handlers._invariant_analysis_handler_interface import (
    InvariantAnalysisHandlerInterface,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.invariant_analysis.model_invariant_analysis_input import (
    ModelInvariantAnalysisInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

__all__ = ["NodeInvariantAnalysisCheckCompute"]


class NodeInvariantAnalysisCheckCompute:
    """Coordination shell: delegates the check to the container-resolved handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        self._handler = container.get_service(
            cast(
                "type[InvariantAnalysisHandlerInterface]",
                InvariantAnalysisHandlerInterface,
            )
        )

    def handle(self, request: ModelInvariantAnalysisInput) -> ModelValidationReport:
        """Return the canonical report for one document."""
        return self._handler.handle(request)
