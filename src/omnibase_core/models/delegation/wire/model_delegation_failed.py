# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation failed terminal wire DTO."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from omnibase_core.models.delegation.wire.model_delegation_result import (
    ModelDelegationResult,
)


class ModelDelegationFailed(ModelDelegationResult):
    """Delegation terminal, FAILED outcome (OMN-14600).

    Thin subclass: adds no new fields. Class identity disambiguates the failed
    topic from the completed topic, while validation rejects an accepted
    quality verdict on a failed terminal.
    """

    @model_validator(mode="after")
    def validate_failed_terminal_truth(self) -> Self:
        """Keep the failed topic identity consistent with its payload."""
        if self.quality_passed:
            msg = "failed delegation requires quality_passed=false"
            raise ValueError(msg)
        return self


__all__: list[str] = ["ModelDelegationFailed"]
