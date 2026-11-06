# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator: each venv is judged against the lock it was built from (OMN-22649)."""

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
from omnibase_core.models.venv_build_lock.model_venv_build_lock_check_input import (
    ModelVenvBuildLockCheckInput,
)
from omnibase_core.models.venv_build_lock.model_venv_build_lock_document import (
    ModelVenvBuildLockDocument,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_venv_build_lock import check_venv_build_lock
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorVenvBuildLock"]


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


class ValidatorVenvBuildLock(ValidatorBase):
    """Read one facts document, read each lock it names, and judge with the pure checker."""

    validator_id: ClassVar[str] = "venv_build_lock"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "venv_build_lock.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            document = ModelVenvBuildLockDocument.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read venv build-lock facts: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        checkout_lock = _read(document.checkout_lock_path)
        if checkout_lock is None:
            raise ModelOnexError(
                message=f"{path}: cannot read the checkout lock {document.checkout_lock_path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        surfaces = tuple(
            surface.model_copy(
                update={"build_lock_text": _read(surface.build_lock_path)}
            )
            for surface in document.surfaces
        )
        result = check_venv_build_lock(
            ModelVenvBuildLockCheckInput(
                source_name=path.as_posix(),
                checkout_lock_text=checkout_lock,
                surfaces=surfaces,
                contract=contract,
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorVenvBuildLock.main())
