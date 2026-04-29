# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract entry model — declared protocol surfaces for a single contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.governance.model_db_table_ref import ModelDbTableRef


class ModelContractEntry(BaseModel):
    """A single contract's declared protocol surfaces."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str
    node_name: str
    subscribe_topics: list[str]
    publish_topics: list[str]
    protocols: list[str]  # EnumInterfaceSurface values
    db_tables: list[ModelDbTableRef] = []
