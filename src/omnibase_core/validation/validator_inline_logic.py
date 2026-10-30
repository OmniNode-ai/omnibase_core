# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorInlineLogic -- refuse inline programs in workflows and contract check values (OMN-21534, K9).

Logic belongs in a node or a core hook, not in a workflow ``run:`` block or a contract
``check_value``. The ``ValidatorBase`` entry of the inline-logic rules: it reads one
workflow or ticket contract, parses its run steps or check values and hands them with
the contract's rule rows to the pure ``checker_inline_logic.check_inline_logic``. The
scan set and every rule value live in ``contracts/inline_logic.validation.yaml``.

Usage (pre-commit hook)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_inline_logic:ValidatorInlineLogic <files...>
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
from omnibase_core.models.inline_logic.model_inline_logic_document import (
    ModelInlineLogicDocument,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_inline_logic import check_inline_logic
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorInlineLogic"]


class ValidatorInlineLogic(ValidatorBase):
    """Read one workflow or ticket contract and judge it against the contract rule rows."""

    validator_id: ClassVar[str] = "inline_logic"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            source = path.read_text(encoding="utf-8")
            document = load_yaml_content_as_model(source, ModelInlineLogicDocument)
        except (OSError, UnicodeDecodeError, ModelOnexError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read workflow or contract: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        return check_inline_logic(
            path, document.run_steps, document.check_values, contract.rules
        )
