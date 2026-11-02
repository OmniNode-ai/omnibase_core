# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorStubImplementations -- stub implementation refusals (OMN-22003).

The ``ValidatorBase`` entry reads one path and hands its path and bytes with
contract rule rows to ``checker_stub_implementations.check_stub_implementations``.
Exemptions, names, thresholds and every diagnostic live in
``contracts/stub_implementations.validation.yaml``.

Usage (pre-commit hook ``check-stub-implementations``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_stub_implementations:ValidatorStubImplementations <paths...>
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_stub_implementations import (
    _text,
    check_stub_implementations,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorStubImplementations"]


class ValidatorStubImplementations(ValidatorBase):
    """Read one path and judge it against the contract's stub rule rows."""

    validator_id: ClassVar[str] = "stub_implementations"

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        """Retain the script CLI's refusal of nonexistent input targets."""
        for target in targets:
            if not target.exists():
                message = _text(self.contract.rules[0], "missing_target_message")
                raise ModelOnexError(
                    message=message.format(path=target),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        return super()._resolve_targets(targets)

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            relative = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            relative = path.as_posix()
        try:
            content = path.read_bytes()
        except OSError:
            # The script skips unreadable files; other validators judge I/O errors.
            return ()
        return check_stub_implementations(path, relative, content, contract.rules)
