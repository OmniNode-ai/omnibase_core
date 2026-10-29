# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorCheckerRuleData -- K10 ``checker_rule_data`` entry (OMN-21503).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_checker_rule_data`:
reads the module and the names beside it, hands them to the pure checker.

    python -m omnibase_core.validation.validator_checker_rule_data [paths...]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_checker_rule_data_module_fact import (
    ModelCheckerRuleDataModuleFact,
)
from omnibase_core.validation.checker_checker_rule_data import check_module
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorCheckerRuleData(ValidatorBase):
    """Refuse rule tables held in a checker, and validators outside the generic format."""

    validator_id: ClassVar[str] = "checker_rule_data"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        fact = ModelCheckerRuleDataModuleFact(
            name=path.name,
            posix_path=path.as_posix(),
            source=path.read_text(encoding="utf-8", errors="replace"),
            sibling_names=_names_in(path.parent),
            contract_names=_names_in(path.parent / "contracts"),
        )
        return check_module(path, fact, {r.rule_id: r for r in contract.rules})


def _names_in(directory: Path) -> frozenset[str]:
    if not directory.is_dir():
        return frozenset()
    return frozenset(p.name for p in directory.iterdir())


if __name__ == "__main__":
    sys.exit(ValidatorCheckerRuleData.main())
