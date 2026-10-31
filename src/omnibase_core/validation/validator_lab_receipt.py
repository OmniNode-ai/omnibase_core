# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for the lab-receipt check (OMN-21823)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_check_input import (
    ModelLabReceiptCheckInput,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_document import (
    ModelLabReceiptDocument,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_lab_receipt import check_lab_receipt
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorLabReceipt"]


class ValidatorLabReceipt(ValidatorBase):
    """Read one facts document and judge it with the pure checker and its contract."""

    validator_id: ClassVar[str] = "lab_receipt"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "lab_receipt.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            document = ModelLabReceiptDocument.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read lab-receipt facts: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        result = check_lab_receipt(
            ModelLabReceiptCheckInput(
                source_name=path.as_posix(), document=document, contract=contract
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorLabReceipt.main())
