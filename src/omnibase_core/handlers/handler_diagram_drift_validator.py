# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""File validator adapter for the pure diagram drift predicate."""

from functools import cached_property
from pathlib import Path

from omnibase_core.handlers.handler_diagram_drift import (
    FragmentLoader,
    HandlerDiagramDrift,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_report import (
    ModelDiagramDriftReport,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_rules import (
    ModelDiagramDriftRules,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorDiagramDrift(ValidatorBase):
    """Load the shipped contract and check Markdown through an injected fragment loader."""

    validator_id = "diagram_drift"

    def __init__(
        self,
        load_fragment: FragmentLoader,
        contract: ModelValidatorSubcontract | None = None,
    ) -> None:
        super().__init__(contract=contract)
        self._load_fragment = load_fragment
        self._handler = HandlerDiagramDrift()

    def _get_contract_path(self) -> Path:
        """Resolve the contract from validation, independently of this module."""
        return (
            Path(__file__).parent.parent
            / "validation"
            / "contracts"
            / "diagram_drift.validation.yaml"
        )

    @cached_property
    def rules(self) -> ModelDiagramDriftRules:
        """The validated rule table, cached for this validator instance."""
        return ModelDiagramDriftRules.from_contract(self.contract)

    def check_document(self, text: str) -> ModelDiagramDriftReport:
        """Check document text without reading a document file."""
        return self._handler.check(text, self.rules, self._load_fragment)

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        """Check Markdown files and attach their path to every reported issue."""
        if path.suffix != ".md":
            return ()
        report = self.check_document(path.read_text(encoding="utf-8"))
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in report.issues
        )
