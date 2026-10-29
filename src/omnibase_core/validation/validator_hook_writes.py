# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorHookWrites -- refuse a pre-commit hook whose entry writes (OMN-21498, T2.6).

A hook checks and refuses; it never rewrites the files it was given. The
``ValidatorBase`` entry of the hook-writes rule: it reads one pre-commit file
(``.pre-commit-config.yaml`` or ``.pre-commit-hooks.yaml``), parses its hooks and
hands them with the contract's rule rows to the pure
``checker_hook_writes.check_hook_writes``. The scan set and every rule value live in
``contracts/hook_writes.validation.yaml``.

Usage (pre-commit hook)::

    python -m omnibase_core.validation.validator_hook_writes <hook files...>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.hook_writes.model_hook_writes_document import (
    ModelHookWritesDocument,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_hook_writes import check_hook_writes
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorHookWrites"]


class ValidatorHookWrites(ValidatorBase):
    """Read one pre-commit file and judge its hooks against the contract rule rows."""

    validator_id: ClassVar[str] = "hook_writes"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            source = path.read_text(encoding="utf-8")
            hooks = load_yaml_content_as_model(source, ModelHookWritesDocument).hooks
        except (OSError, UnicodeDecodeError, ModelOnexError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read hooks: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        return check_hook_writes(path, hooks, contract.rules)


if __name__ == "__main__":
    from omnibase_core.handlers.handler_validator_run import (
        build_validator_container,
        main,
    )

    sys.exit(main(ValidatorHookWrites, container_factory=build_validator_container))
