# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation completed terminal wire DTO."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from omnibase_core.models.delegation.wire.model_delegation_result import (
    ModelDelegationResult,
)


class ModelDelegationCompleted(ModelDelegationResult):
    """Delegation terminal, COMPLETED outcome (OMN-14600).

    Thin subclass: adds no new fields. Class identity disambiguates the
    completed topic from the failed topic, while validation rejects terminal
    failure causes on completed outcomes.
    """

    @model_validator(mode="after")
    def validate_completed_terminal_truth(self) -> Self:
        """Keep the completed topic identity consistent with its payload."""
        if self.terminal_failure_cause is not None:
            msg = "completed delegation cannot carry terminal_failure_cause"
            raise ValueError(msg)
        if self.terminal_failure_reason is not None:
            msg = "completed delegation cannot carry terminal_failure_reason"
            raise ValueError(msg)
        if self.failure_reason:
            msg = "completed delegation cannot carry failure_reason"
            raise ValueError(msg)
        if not self.quality_passed:
            msg = "completed delegation requires quality_passed"
            raise ValueError(msg)
        return self


__all__: list[str] = ["ModelDelegationCompleted"]
