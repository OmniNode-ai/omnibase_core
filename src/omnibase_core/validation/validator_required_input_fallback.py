# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRequiredInputFallback -- ``required_input_fallback`` entry (OMN-24538, fail-open ratchets).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_required_input_fallback`: it
finds the contract of the node a module belongs to (the nearest ancestor directory holding the
contract file the rule row names), hands the input names that contract marks required with the
module's source to the pure checker, and holds the module to its entry in
the baseline file its rule row names (``.onex_ratchets/required_input_fallback_baseline.yaml`` when a repository adopts the hook with findings). A contract that exists but cannot be read
or parsed raises instead of passing the module clean; with no ancestor contract the module is judged
clean. The scope and every rule value live in ``contracts/required_input_fallback.validation.yaml``.

Usage (pre-commit hook ``required-input-fallback``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_required_input_fallback:ValidatorRequiredInputFallback --baseline .onex_ratchets/required_input_fallback_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_required_input_fallback import (
    RULE_REQUIRED_INPUT_FALLBACK,
    check_required_input_fallback,
    required_inputs,
)
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorRequiredInputFallback"]


class ValidatorRequiredInputFallback(ValidatorBaselinedDetector):
    """Read one module and judge it against the node's required inputs and its baseline entry."""

    validator_id: ClassVar[str] = "required_input_fallback"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_required_input_fallback(
            path, source, self._required(path, rules), rules
        )

    def _required(
        self, path: Path, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[str, ...]:
        """The input names the node's contract marks required; empty when no ancestor holds it."""
        row = rules.get(RULE_REQUIRED_INPUT_FALLBACK)
        if row is None or not row.enabled:
            return ()
        contract_file = rule_string(row, "contract_file")
        absolute = (self._root / path).resolve()
        for directory in absolute.parents:
            if not directory.is_relative_to(self._root):
                break
            contract = directory / contract_file
            if contract.is_file():
                return required_inputs(_read_contract(contract))
        return ()


def _read_contract(path: Path) -> str:
    """The contract's text; a contract that exists but cannot be read raises."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ModelOnexError(
            message=f"{path}: cannot read the node contract: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
