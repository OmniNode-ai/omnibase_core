# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorActionPin -- the contract carrier of the action-pin check (OMN-17427, OMN-21518).

The rule data of the check lives in ``contracts/action_pin.validation.yaml``; this
``ValidatorBase`` entry loads it and ``checker_action_pin.action_pin_rules`` types it.
The verdict is the pure ``HandlerActionPin`` of ``node_action_pin_check_effect``, run by
``runtime_action_pin_check`` (hook ``check-action-pins``).
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorActionPin"]


class ValidatorActionPin(ValidatorBase):
    """Loads the action-pin validation contract; the node handler judges the files."""

    validator_id: ClassVar[str] = "action_pin"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """No per-file rule exists here: the verdict needs the repository overlay."""
        return ()
