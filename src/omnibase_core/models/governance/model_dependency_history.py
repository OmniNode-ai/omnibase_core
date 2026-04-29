# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dependency history — accumulated state from dependency reducer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.governance.model_contract_dependency_output import (
    ModelContractDependencyOutput,
)
from omnibase_core.models.governance.model_dependency_snapshot import (
    ModelDependencySnapshot,
)
from omnibase_core.models.governance.model_hotspot_topic import ModelHotspotTopic


class ModelDependencyHistory(BaseModel):
    """Accumulated dependency state over time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: str  # "stable" or "hotspot_detected"
    snapshots: list[ModelDependencySnapshot]
    persistent_hotspots: list[
        ModelHotspotTopic
    ]  # topics that are hotspots in 3+ consecutive snapshots
    latest: ModelContractDependencyOutput | None = None
