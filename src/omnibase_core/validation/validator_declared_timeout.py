# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorDeclaredTimeout -- ``declared_timeout`` entry (OMN-23187, validators plan).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_declared_timeout`: it finds the
contract of the node a module belongs to (the nearest ancestor directory holding the contract file the
rule row names) and that node's overlay files, hands the limit keys they declare with the module's
source to the pure checker, and holds the module to its entry in
``.onex_ratchets/declared_timeout_baseline.yaml``. The scope and every rule value live in
``contracts/declared_timeout.validation.yaml``.

Usage (pre-commit hook ``declared-timeout-reaches-call``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_declared_timeout:ValidatorDeclaredTimeout --baseline .onex_ratchets/declared_timeout_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_declared_timeout import (
    RULE_DECLARED_TIMEOUT,
    check_declared_timeout,
    declared_timeout_keys,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorDeclaredTimeout"]


class ValidatorDeclaredTimeout(ValidatorBaselinedDetector):
    """Read one module and judge it against the node's declared limit and its baseline entry."""

    validator_id: ClassVar[str] = "declared_timeout"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        declared = declared_timeout_keys(self._node_texts(path, rules), rules)
        return check_declared_timeout(path, source, declared, rules)

    def _node_texts(
        self, path: Path, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[str, ...]:
        """The node's contract and overlay texts; empty when no ancestor holds the contract file."""
        row = rules.get(RULE_DECLARED_TIMEOUT)
        if row is None or not row.enabled:
            return ()
        contract_file = rule_string(row, "contract_file")
        overlay_globs = rule_strings(row, "overlay_globs")
        absolute = (self._root / path).resolve()
        for directory in absolute.parents:
            if not directory.is_relative_to(self._root):
                break
            contract = directory / contract_file
            if contract.is_file():
                files = [contract]
                for pattern in overlay_globs:
                    files.extend(sorted(directory.glob(pattern)))
                return tuple(_read(f) for f in files)
        return ()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
