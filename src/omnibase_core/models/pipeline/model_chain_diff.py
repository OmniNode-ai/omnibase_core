# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Chain diff model for golden chain verification."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pipeline.model_golden_chain_entry import ModelGoldenChainEntry

__all__ = ["ModelChainDiff"]


class ModelChainDiff(BaseModel):
    """Diff between an expected golden chain and an observed event chain."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    matches: bool
    expected_count: int
    observed_count: int
    missing_events: tuple[ModelGoldenChainEntry, ...] = Field(default_factory=tuple)
    unexpected_events: tuple[ModelGoldenChainEntry, ...] = Field(default_factory=tuple)
    order_mismatches: tuple[str, ...] = Field(default_factory=tuple)
    topic_mismatches: tuple[str, ...] = Field(default_factory=tuple)
