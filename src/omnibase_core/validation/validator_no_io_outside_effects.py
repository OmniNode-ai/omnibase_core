# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorNoIoOutsideEffects -- K4 ``no_io_outside_effects`` in the generic format (OMN-21532).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_no_io_outside_effects`.
A target is a ``contract.yaml`` (judged alone) or a ``.py`` module (judged against the
nearest ``contract.yaml`` above it). The validator reads; the checker judges; the report
writer and the bus come from the container in the runtime that runs it.

Usage (pre-commit hook)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_no_io_outside_effects:ValidatorNoIoOutsideEffects <paths...>
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_no_io_outside_effects_facts import (
    ModelNoIoOutsideEffectsFacts,
)
from omnibase_core.validation.checker_no_io_outside_effects import (
    RULE_SCOPE,
    check_no_io_outside_effects,
)
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorNoIoOutsideEffects"]


class ValidatorNoIoOutsideEffects(ValidatorBase):
    """Refuse I/O in every module of a node package whose contract is not EFFECT."""

    validator_id: ClassVar[str] = "no_io_outside_effects"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        root: Path | None = None,
    ) -> None:
        super().__init__(contract)
        self._root = (root or Path.cwd()).resolve()

    def _source(self, path: Path) -> ModelSourceFile:
        """The file's text under its path relative to the root, so locations are stable."""
        resolved = path.resolve()
        shown = (
            resolved.relative_to(self._root)
            if resolved.is_relative_to(self._root)
            else path
        )
        return ModelSourceFile(
            path=shown.as_posix(),
            source=path.read_text(encoding="utf-8", errors="replace"),
        )

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        name = rule_string(rules[RULE_SCOPE], "contract_filename")
        if path.name == name:
            return check_no_io_outside_effects(
                ModelNoIoOutsideEffectsFacts(contract=self._source(path)), rules
            )
        for parent in path.resolve().parents:
            candidate = parent / name
            if candidate.is_file():
                return check_no_io_outside_effects(
                    ModelNoIoOutsideEffectsFacts(
                        contract=self._source(candidate), module=self._source(path)
                    ),
                    rules,
                )
        return ()
