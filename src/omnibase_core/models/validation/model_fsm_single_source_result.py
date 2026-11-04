# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of checking an FSM's source of truth."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelFsmSingleSourceResult(BaseModel):
    """Validation issues and state names in contract declaration order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...]
    state_names: tuple[str, ...]

    @property
    def exit_code(self) -> int:
        """Return failure when the check produced any issue."""
        return 1 if self.issues else 0
