# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for the collaborator-lane check (OMN-21599)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.collaborator_lane.model_collaborator_lane_check_input import (
    ModelCollaboratorLaneCheckInput,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_collaborator_lane import check_collaborator_lane
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorCollaboratorLane"]


class ValidatorCollaboratorLane(ValidatorBase):
    """Read one document and judge it with the pure checker."""

    validator_id: ClassVar[str] = "collaborator_lane"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "collaborator_lane.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ()
        result = check_collaborator_lane(
            ModelCollaboratorLaneCheckInput(
                source_name=path.as_posix(), text=text, contract=contract
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorCollaboratorLane.main())
