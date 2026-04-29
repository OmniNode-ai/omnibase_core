# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract overlap edge model — overlap between two contracts sharing protocol surfaces."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, computed_field

_EDGE_NAMESPACE = uuid.UUID("c3d4e5f6-a7b8-9012-cdef-234567890abc")


class ModelContractOverlapEdge(BaseModel):
    """An overlap edge between two contracts sharing protocol surfaces.

    overlap_type values: "topic_producer_consumer", "topic_co_consumer",
        "topic_co_producer", "db_table_shared_write", "db_table_read_write",
        "protocol", "mixed"
    direction values: "producer_to_consumer", "co_consumer",
        "co_producer", "bidirectional"
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_a_repo: str
    node_a_name: str
    node_b_repo: str
    node_b_name: str
    shared_topics: list[str]
    shared_protocols: list[str]
    shared_db_tables: list[str] = []
    overlap_type: str  # see docstring for valid values
    # "producer_to_consumer", "co_consumer", "co_producer", "bidirectional"
    direction: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def edge_id(self) -> uuid.UUID:
        pair = sorted(
            [
                f"{self.node_a_repo}/{self.node_a_name}",
                f"{self.node_b_repo}/{self.node_b_name}",
            ]
        )
        surfaces = sorted(
            self.shared_topics + self.shared_protocols + self.shared_db_tables
        )
        key = f"{pair[0]}|{pair[1]}|{self.direction}|{','.join(surfaces)}"
        return uuid.uuid5(_EDGE_NAMESPACE, key)
