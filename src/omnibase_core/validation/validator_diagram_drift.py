# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for the diagram-drift check (OMN-21510)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_check_input import (
    ModelDiagramDriftCheckInput,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_diagram_drift import check_diagram_drift
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorDiagramDrift"]


class ValidatorDiagramDrift(ValidatorBase):
    """Read one document and judge its diagrams with the pure checker and committed rules."""

    validator_id: ClassVar[str] = "diagram_drift"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "diagram_drift.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ()
        result = check_diagram_drift(
            ModelDiagramDriftCheckInput(
                source_name=path.as_posix(), text=text, contract=contract
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorDiagramDrift.main())
