# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorCiSummaryVerdict -- ``ci_summary_verdict`` entry (OMN-17864).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_ci_summary_verdict`. A rows file
(``ci_summary_rows*.json``, written by the CI Summary job) is judged by the jobs and external rules; any
other file is judged by the parity rule. Exit 0 green, 1 red (error issues), 2 pending (warning issues)::

    python -m omnibase_core.validation.validator_ci_summary_verdict ci_summary_rows.json
    python -m omnibase_core.validation.validator_ci_summary_verdict <repo checkout>   # parity
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_ci_summary_verdict import (
    RULE_JOBS,
    check_parity,
    check_rows,
)
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorCiSummaryVerdict"]


class ValidatorCiSummaryVerdict(ValidatorBase):
    """Judge a rows file as the CI Summary verdict, any other file for a copy of the gate."""

    validator_id: ClassVar[str] = "ci_summary_verdict"

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        jobs = rules.get(RULE_JOBS)
        if jobs is not None and re.search(
            rule_string(jobs, "rows_file_pattern"), path.as_posix()
        ):
            return self._rows(path, rules)
        source = path.read_text(encoding="utf-8", errors="replace")
        return check_parity(path, source, rules)

    def _rows(
        self, path: Path, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            facts = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return (_refusal(path, f"rows file unreadable: {exc}"),)
        if not isinstance(facts, dict):
            return (_refusal(path, "rows file must hold one JSON object"),)
        return check_rows(path, facts, rules)


def _refusal(path: Path, message: str) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=EnumSeverity.ERROR,
        message=message,
        code="ci_summary_rows_unreadable",
        file_path=path,
        rule_name="ci_summary_jobs",
    )


if __name__ == "__main__":
    sys.exit(ValidatorCiSummaryVerdict.main())
