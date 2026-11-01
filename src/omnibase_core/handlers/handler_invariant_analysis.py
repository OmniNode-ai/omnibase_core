# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure canonical report handler for invariant analysis (OMN-21565)."""

from __future__ import annotations

from typing import cast

from omnibase_core.handlers._invariant_analysis_rules_interface import (
    InvariantAnalysisRulesInterface,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.invariant_analysis.model_invariant_analysis_input import (
    ModelInvariantAnalysisInput,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_rules import (
    ModelInvariantAnalysisRules,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = ["HandlerInvariantAnalysis"]


class HandlerInvariantAnalysis:
    """Evaluate injected facts with the supplied contract, without I/O."""

    def __init__(self, container: ModelONEXContainer) -> None:
        """Resolve the pure rule function from the container."""
        self._analyse = container.get_service(
            cast(
                "type[InvariantAnalysisRulesInterface[ModelInvariantAnalysisInput, ModelInvariantAnalysisRules, tuple[ModelValidationFindingEmbed, ...]]]",
                InvariantAnalysisRulesInterface,
            )
        )

    def handle(self, request: ModelInvariantAnalysisInput) -> ModelValidationReport:
        """Return ERROR for findings and PASS for an empty result."""
        rules = ModelInvariantAnalysisRules.from_contract(request.contract)
        return ModelValidationReport.from_findings(
            findings=self._analyse(request, rules),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(request.contract.validator_id,),
        )
