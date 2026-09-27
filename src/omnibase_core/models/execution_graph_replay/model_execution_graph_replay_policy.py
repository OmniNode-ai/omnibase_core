# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Explicit deterministic traversal, identity, and deduplication policy."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelExecutionGraphReplayPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    traversal: Literal["parent_topological"]
    tie_break: tuple[
        Literal["declared_hop_position"],
        Literal["topic_partition_kafka_offset"],
        Literal["envelope_id"],
    ] = (
        "declared_hop_position",
        "topic_partition_kafka_offset",
        "envelope_id",
    )
    node_identity: Literal["envelope_id"]
    redelivery: Literal["same_id_exact_redelivery_lowest_source_position"]
    conflicting_identity: Literal["same_id_conflicting_parent_or_semantic_body_refuse"]
    cross_topic_duplicate: Literal["same_id_across_topics_refuse"]
