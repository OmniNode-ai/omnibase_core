# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic contract-driven validator for shared pre-commit hook pins."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.precommit_pins.model_precommit_pin_parity_input import (
    ModelPrecommitPinParityInput,
)
from omnibase_core.models.precommit_pins.model_precommit_pin_rules import (
    ModelPrecommitPinRules,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time_request import (
    ModelPrecommitRevTimeRequest,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time_result import (
    ModelPrecommitRevTimeResult,
)
from omnibase_core.validation.checker_precommit_pin_parity import (
    candidate_pins,
    check_precommit_pin_parity,
    extract_pins,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorPrecommitPinParity(ValidatorBase):
    """Read config facts, resolve times through DI, and invoke the pure checker."""

    validator_id: ClassVar[str] = "precommit_pin_parity"

    def __init__(
        self,
        resolver: Callable[[ModelPrecommitRevTimeRequest], ModelPrecommitRevTimeResult],
        contract: ModelValidatorSubcontract | None = None,
        *,
        contract_path: Path | None = None,
        history_repo: str | None = None,
        cache_home: str | None = None,
    ) -> None:
        self.contract_path = contract_path
        super().__init__(contract)
        self.rules = ModelPrecommitPinRules.from_contract(self.contract)
        self.resolver = resolver
        self.history_repo = history_repo
        self.cache_home = cache_home

    def _get_contract_path(self) -> Path:
        if self.contract_path is not None:
            return self.contract_path
        return super()._get_contract_path()

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        for path in targets:
            if not path.exists():
                raise ModelOnexError(
                    message=f"target does not exist: {path}",
                    error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                )
        return [
            path
            for path in super()._resolve_targets(targets)
            if any(path.match(pattern) for pattern in self.contract.target_patterns)
        ]

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        rules = ModelPrecommitPinRules.from_contract(contract)
        source = path.read_text(encoding="utf-8")
        parameters = rules.lookup
        if self.history_repo is not None:
            parameters = parameters.model_copy(
                update={"history_repo": self.history_repo}
            )
        times = self.resolver(
            ModelPrecommitRevTimeRequest(
                pins=candidate_pins(extract_pins(source), rules),
                parameters=parameters,
                cache_home=self.cache_home,
            )
        )
        return check_precommit_pin_parity(
            ModelPrecommitPinParityInput(
                rules=rules, path=str(path), source=source, rev_times=times.rev_times
            )
        )
