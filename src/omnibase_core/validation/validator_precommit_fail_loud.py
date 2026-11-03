# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorPrecommitFailLoud -- refuse a hook that swallows its failure (OMN-22357).

The ``ValidatorBase`` entry of the fail-loud meta rule. It reads one pre-commit file
(``.pre-commit-config.yaml`` or ``.pre-commit-hooks.yaml``), parses its hooks, reads
the gate scripts their entries invoke, and hands them with the contract's rule rows
to the pure ``checker_precommit_fail_loud.check_precommit_fail_loud``. The scan set
and every rule value live in ``contracts/precommit_fail_loud.validation.yaml``; this
module names no hook and no repository.

Usage (pre-commit hook)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_precommit_fail_loud:ValidatorPrecommitFailLoud <hook files...>
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
from omnibase_core.models.precommit_fail_loud.model_fail_loud_document import (
    ModelFailLoudDocument,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_precommit_fail_loud import (
    check_precommit_fail_loud,
    referenced_scripts,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorPrecommitFailLoud"]


class ValidatorPrecommitFailLoud(ValidatorBase):
    """Read one pre-commit file and judge its hooks against the contract rule rows."""

    validator_id: ClassVar[str] = "precommit_fail_loud"

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        for path in targets:
            if not path.exists():
                raise ModelOnexError(
                    message=f"target does not exist: {path}",
                    error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                )
        patterns = self.contract.target_patterns
        for path in targets:
            if path.is_file() and not any(
                path.resolve().match(pattern) for pattern in patterns
            ):
                # A file named on the command line that no pattern covers would be
                # dropped and the run would print PASS having checked nothing.
                raise ModelOnexError(
                    message=f"target is not covered by target_patterns {patterns}: {path}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        return super()._resolve_targets(targets)

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            document = load_yaml_content_as_model(
                path.read_text(encoding="utf-8"), ModelFailLoudDocument
            )
        except (OSError, UnicodeDecodeError, ModelOnexError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read hooks: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        scripts: dict[str, str] = {}
        for token in referenced_scripts(document, contract.rules):
            script = path.parent / token
            if script.is_file():
                scripts[token] = script.read_text(encoding="utf-8")
        return check_precommit_fail_loud(path, document, scripts, contract.rules)
