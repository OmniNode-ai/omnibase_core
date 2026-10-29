# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorBindingConformance: ValidatorBase entry over the pure binding conformance checker (OMN-21514).

The rule tables are ``validation/contracts/binding_conformance.validation.yaml``; the predicate is
``omnibase_core.validation.checker_binding_conformance``. Pre-commit and CI run this module with the
handler files to check; ``check`` takes a full request (contracts, tables, private names).
"""

from __future__ import annotations

import sys
from pathlib import Path

from omnibase_core.enums.enum_binding_source_kind import EnumBindingSourceKind
from omnibase_core.models.binding_conformance.model_binding_conformance_request import (
    ModelBindingConformanceRequest,
)
from omnibase_core.models.binding_conformance.model_binding_conformance_result import (
    ModelBindingConformanceResult,
)
from omnibase_core.models.binding_conformance.model_binding_source import (
    ModelBindingSource,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_binding_conformance import (
    binding_rules_from_contract,
    check_binding_conformance,
    check_source_text,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorBindingConformance(ValidatorBase):
    """Apply the binding contract to supplied requests or handler files."""

    validator_id = "binding_conformance"

    def check(
        self, request: ModelBindingConformanceRequest
    ) -> ModelBindingConformanceResult:
        """Check supplied text against this validator's contract."""
        return check_binding_conformance(
            request, binding_rules_from_contract(self.contract)
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        """Report Python handler literal violations with contract severities."""
        if path.suffix != ".py" or not (
            path.name.startswith("handler") or path.parent.name == "handlers"
        ):
            return ()
        source = ModelBindingSource(
            node=path.parent.name or "-",
            path=str(path),
            kind=EnumBindingSourceKind.HANDLER,
            text=path.read_text(encoding="utf-8"),
        )
        rules = binding_rules_from_contract(contract)
        return tuple(
            ModelValidationIssue(
                severity=rules.severity_of(issue.rule),
                message=issue.detail,
                code=issue.rule.value,
                rule_name=issue.rule.value,
                file_path=path,
                line_number=issue.line or None,
            )
            for issue in check_source_text(source, rules)
        )


if __name__ == "__main__":
    sys.exit(ValidatorBindingConformance.main())
