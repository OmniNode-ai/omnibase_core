# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts-file I/O boundary for the pure delivery reference checker."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_delivery_reference import (
    check_delivery_paths,
    reconcile_consumers,
    to_validation_issues,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.delivery import ModelDeliveryFacts
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorDeliveryReference", "main"]


class ValidatorDeliveryReference(ValidatorBase):
    """Load consumer facts and enforce their declared delivery_paths overlay."""

    validator_id = "delivery_reference"

    def _get_contract_path(self) -> Path:
        return (
            Path(__file__).resolve().parents[1]
            / "validation"
            / "contracts"
            / "delivery_reference.validation.yaml"
        )

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        """Retain missing explicit targets so unreadable facts fail closed."""
        resolved = set(super()._resolve_targets(targets))
        resolved.update(target.resolve() for target in targets if not target.exists())
        return sorted(resolved)

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            facts = load_and_validate_yaml_model(path, ModelDeliveryFacts)
        except (OSError, ValueError, ModelOnexError) as exc:
            # Facts must remain fail-closed even if a custom contract disables this rule.
            _, severity = self._get_rule_config(
                "delivery_reference_facts_unreadable", contract
            )
            return (
                ModelValidationIssue(
                    severity=severity
                    if severity.is_error_or_above()
                    else EnumSeverity.ERROR,
                    message=f"Cannot read delivery facts {path}: {exc}",
                    code="facts_unreadable",
                    file_path=path,
                    rule_name="delivery_reference_facts_unreadable",
                ),
            )
        verdicts = tuple(
            dict.fromkeys(check_delivery_paths(facts) + reconcile_consumers(facts))
        )
        issues: list[ModelValidationIssue] = []
        for issue in to_validation_issues(verdicts):
            enabled, severity = self._get_rule_config(issue.rule_name, contract)
            if enabled:
                issues.append(
                    issue.model_copy(update={"severity": severity, "file_path": path})
                )
        return tuple(issues)


def main() -> NoReturn:
    """Run the shared validator CLI and exit with its verdict."""
    sys.exit(ValidatorDeliveryReference.main())


if __name__ == "__main__":
    main()
