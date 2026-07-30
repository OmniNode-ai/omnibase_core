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
    def validate_no_terminal_failure_cause(self) -> Self:
        """A completed terminal cannot simultaneously name a failure cause."""
        if self.terminal_failure_cause is not None:
            msg = "completed delegation cannot carry terminal_failure_cause"
            raise ValueError(msg)
        return self


__all__: list[str] = ["ModelDelegationCompleted"]
