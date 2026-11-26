# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Result of the consumer install check (OMN-26670)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.consumer_install_check.model_consumer_outcome import (
    ModelConsumerOutcome,
)


class ModelConsumerInstallResult(BaseModel):
    """Pass or fail of one candidate across every consumer, with the time it took."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    candidate_distribution: str
    passed: bool
    outcomes: tuple[ModelConsumerOutcome, ...]
    elapsed_seconds: float = Field(ge=0)
    budget_seconds: float = Field(gt=0)
    over_budget: bool
    failure_lines: tuple[str, ...] = ()
