# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Declared, intentional divergence between two event registries (OMN-21416)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEventRegistryDriftBaseline"]


class ModelEventRegistryDriftBaseline(BaseModel):
    """Carve-outs the drift check does not report.

    Attributes:
        event_source_only: Event types allowed on the source side only.
        event_registry_only: Event types allowed on the registry side only.
        source_only_topics: Topics allowed on the source side only.
        registry_only_topics: Topics allowed on the registry side only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_source_only: frozenset[str] = Field(default_factory=frozenset)
    event_registry_only: frozenset[str] = Field(default_factory=frozenset)
    source_only_topics: frozenset[str] = Field(default_factory=frozenset)
    registry_only_topics: frozenset[str] = Field(default_factory=frozenset)
