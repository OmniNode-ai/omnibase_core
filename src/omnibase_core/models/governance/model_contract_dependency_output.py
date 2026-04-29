# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model for contract dependency computation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.governance.model_contract_entry import ModelContractEntry
from omnibase_core.models.governance.model_contract_overlap_edge import (
    ModelContractOverlapEdge,
)
from omnibase_core.models.governance.model_dependency_wave import ModelDependencyWave
from omnibase_core.models.governance.model_hotspot_topic import ModelHotspotTopic


class ModelContractDependencyOutput(BaseModel):
    """Contract overlap graph: dependency edges and parallel wave groups."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entries: list[ModelContractEntry]
    edges: list[ModelContractOverlapEdge]
    waves: list[ModelDependencyWave]
    hotspot_topics: list[ModelHotspotTopic]
