# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for the plan-invariant check (OMN-21559)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.plan_invariant.model_plan_invariant_check_input import (
    ModelPlanInvariantCheckInput,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_plan_invariant import check_plan_invariant
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_task_criteria import ValidatorTaskCriteria

__all__ = ["ValidatorPlanInvariant"]


class ValidatorPlanInvariant(ValidatorBase):
    """Read one plan and judge it with the pure checker and committed K12 rules."""

    validator_id: ClassVar[str] = "plan_invariant"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "plan_invariant.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ()
        result = check_plan_invariant(
            ModelPlanInvariantCheckInput(
                source_name=path.as_posix(),
                text=text,
                contract=contract,
                task_criteria_contract=ValidatorTaskCriteria().contract,
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorPlanInvariant.main())
