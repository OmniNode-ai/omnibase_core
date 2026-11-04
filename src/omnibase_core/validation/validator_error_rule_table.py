# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""File adapter for the error-rule checker, run by the existing validation node."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import TypeAdapter

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.error_rule_table.model_error_action_contract import (
    ModelErrorActionContract,
)
from omnibase_core.models.error_rule_table.model_error_action_registry import (
    ModelErrorActionRegistry,
)
from omnibase_core.models.error_rule_table.model_error_rule_check_input import (
    ModelErrorRuleCheckInput,
)
from omnibase_core.models.error_rule_table.model_error_rule_measurement import (
    ModelErrorRuleMeasurement,
)
from omnibase_core.overlays.contract_env_ref import (
    contract_env_reference,
    resolve_contract_env_binding,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_error_rule_table import (
    check_error_rule_table,
    error_rule_policy,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorErrorRuleTable(ValidatorBase):
    """Load trusted registries separately from the row document, with injectable facts.

    The composition boundary supplies registries from protected artifacts, never from
    a table row. Unset paths resolve to empty registries, refusing rows that need them.
    An injected context replaces file lookup, reusing the runtime's overlay/DI wiring.
    """

    validator_id: ClassVar[str] = "error_rule_table"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        context: ModelErrorRuleCheckInput | None = None,
    ) -> None:
        super().__init__(contract)
        self._context = context

    def _context_from_files(
        self, contract: ModelValidatorSubcontract
    ) -> ModelErrorRuleCheckInput:
        request = ModelErrorRuleCheckInput(document={}, contract=contract)
        policy = error_rule_policy(request)
        contracts: dict[str, ModelErrorActionContract] = {}
        state_checks: frozenset[str] = frozenset()
        retired_ids: frozenset[str] = frozenset()
        registry_path = resolve_contract_env_binding(
            contract_env_reference(policy.registry_env)
        ).value
        if registry_path:
            registry = load_yaml_mapping_no_duplicates(
                Path(registry_path).read_text(encoding="utf-8"), source=registry_path
            )
            parsed = ModelErrorActionRegistry.model_validate(registry)
            contracts = parsed.contracts
            if any(not check.strip() for check in parsed.state_checks):
                raise ModelOnexError(
                    message="state_checks: registry must list nonblank check ids",
                    error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                )
            state_checks = frozenset(parsed.state_checks)
            retired_ids = parsed.retired_ids
        sources: set[str] = set()
        ledger_path = resolve_contract_env_binding(
            contract_env_reference(policy.sources_env)
        ).value
        if ledger_path:
            for line in Path(ledger_path).read_text(encoding="utf-8").splitlines():
                cells = [cell.strip() for cell in line.split("|")]
                if len(cells) < 3 or cells[1] not in policy.source_record_types:
                    continue
                sources.add(f"ledger:{cells[0]}")
                sources.update(
                    f"ticket:{cell.removeprefix('ticket=')}"
                    for cell in cells[2:]
                    if cell.startswith("ticket=")
                )
        measurements: dict[str, ModelErrorRuleMeasurement] = {}
        measured_path = resolve_contract_env_binding(
            contract_env_reference(policy.measurements_env)
        ).value
        if measured_path:
            raw = load_yaml_mapping_no_duplicates(
                Path(measured_path).read_text(encoding="utf-8"), source=measured_path
            )
            measurements = TypeAdapter(
                dict[str, ModelErrorRuleMeasurement]
            ).validate_python(raw)
        authorized_modes: dict[str, str] = {}
        modes_path = resolve_contract_env_binding(
            contract_env_reference(policy.modes_env)
        ).value
        if modes_path:
            modes = load_yaml_mapping_no_duplicates(
                Path(modes_path).read_text(encoding="utf-8"), source=modes_path
            )
            authorized_modes = TypeAdapter(dict[str, str]).validate_python(modes)
        return ModelErrorRuleCheckInput(
            document={},
            contract=contract,
            action_contracts=contracts,
            resolved_sources=frozenset(sources),
            registered_state_checks=state_checks,
            measurements=measurements,
            authorized_modes=authorized_modes,
            retired_ids=retired_ids,
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            error_rule_policy(ModelErrorRuleCheckInput(document={}, contract=contract))
        except (ValueError, ModelOnexError) as exc:
            raise ModelOnexError(
                message=f"error_rule_table contract: {exc}",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            ) from exc
        try:
            document = load_yaml_mapping_no_duplicates(
                path.read_text(encoding="utf-8"), source=str(path)
            )
            context = self._context or self._context_from_files(contract)
            issues = check_error_rule_table(
                context.model_copy(update={"document": document, "contract": contract})
            )
        except (
            OSError,
            UnicodeError,
            ValueError,
            yaml.YAMLError,
            ModelOnexError,
        ) as exc:
            rule = next(
                rule
                for rule in contract.rules
                if rule.rule_id == "error_rule_table_invalid"
            )
            issues = (
                ModelValidationIssue(
                    severity=rule.severity,
                    code=rule.rule_id,
                    rule_name=rule.rule_id,
                    message=f"error_rules: {exc}",
                ),
            )
        return tuple(issue.model_copy(update={"file_path": path}) for issue in issues)
