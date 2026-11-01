# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Container-resolved interface of the invariant-analysis handler (OMN-21565)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.models.invariant_analysis.model_invariant_analysis_input import (
    ModelInvariantAnalysisInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

__all__ = ["InvariantAnalysisHandlerInterface"]


@runtime_checkable
class InvariantAnalysisHandlerInterface(Protocol):
    """The handler that evaluates one document."""

    def handle(self, request: ModelInvariantAnalysisInput) -> ModelValidationReport:
        """Return the canonical report for one document."""
        ...
