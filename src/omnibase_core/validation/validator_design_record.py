# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for the design-record check (OMN-21509)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.design_record.model_design_record_check_input import (
    ModelDesignRecordCheckInput,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_design_record import check_design_record
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorDesignRecord(ValidatorBase):
    """Validate design-record files using the pure checker."""

    validator_id: ClassVar[str] = "design_record"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "design_record.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ()
        result = check_design_record(
            ModelDesignRecordCheckInput(text=text, contract=contract)
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorDesignRecord.main())
