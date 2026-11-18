# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorUnreadOutcomeDeclared -- ``unread_outcome_declared`` entry (OMN-24538, fail-open ratchets).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_unread_outcome_declared`: it
reads one contract and hands its source, with a resolver that reads the test file the contract's
``unread_outcome`` names under the root, to the pure checker, and holds the contract to its entry in
``.onex_ratchets/unread_outcome_declared_baseline.yaml``. The scope and every rule value live in
``contracts/unread_outcome_declared.validation.yaml``.

Usage (pre-commit hook ``unread-outcome-declared``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_unread_outcome_declared:ValidatorUnreadOutcomeDeclared --baseline .onex_ratchets/unread_outcome_declared_baseline.yaml <files...>
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
from omnibase_core.validation.checker_unread_outcome_declared import (
    check_unread_outcome_declared,
)
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorUnreadOutcomeDeclared"]


class ValidatorUnreadOutcomeDeclared(ValidatorBaselinedDetector):
    """Read one contract and judge it against its declared unread outcome and its baseline entry."""

    validator_id: ClassVar[str] = "unread_outcome_declared"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_unread_outcome_declared(path, source, self._resolve_test, rules)

    def _resolve_test(self, relative: str) -> str | None:
        """The named test file's source under the root; ``None`` when it does not exist.

        A path that leaves the root names no test file of this repository. A file that exists but
        cannot be read raises instead of judging the contract clean.
        """
        target = (self._root / relative).resolve()
        if not target.is_relative_to(self._root) or not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ModelOnexError(
                message=f"{target}: cannot read the test the unread_outcome names: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
