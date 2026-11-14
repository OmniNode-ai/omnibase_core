# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorStagedPathPolicy -- staged paths refused by path alone (OMN-22012, T2.4).

The ``ValidatorBase`` entry of the hooks ``no-env-file`` and ``no-planning-docs``,
which were a shell script and an inline ``bash -c`` command. Each staged path is
judged by its repository-relative path against the ``path_refused`` rule rows of
``contracts/staged_path_policy.validation.yaml`` through the pure
``checker_commit_hygiene.check_commit_hygiene``. The file is never read: a staged
``.env`` file may hold secrets, and its path is the whole fact. Every pattern and
remediation text is a rule-row parameter; a row of any other kind fails to load.

Usage (pre-commit hooks ``no-env-file`` and ``no-planning-docs``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_staged_path_policy:ValidatorStagedPathPolicy <paths...>
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
from omnibase_core.validation.checker_commit_hygiene import check_commit_hygiene
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorStagedPathPolicy"]

_PATH_KIND = "path_refused"


class ValidatorStagedPathPolicy(ValidatorBase):
    """Judge one staged path, without reading it, against the refused-path rule rows."""

    validator_id: ClassVar[str] = "staged_path_policy"

    def _load_contract(self) -> ModelValidatorSubcontract:
        contract = super()._load_contract()
        for rule in contract.rules:
            kind = (rule.parameters or {}).get("kind")
            if kind != _PATH_KIND:
                raise ModelOnexError(
                    message=(
                        f"staged_path_policy rule {rule.rule_id!r}: kind {kind!r} "
                        f"is not {_PATH_KIND!r}; this validator judges paths only"
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        return contract

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            relative = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            relative = path.as_posix()
        return check_commit_hygiene(path, relative, b"", contract.rules)
