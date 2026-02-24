# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Core event model for Linear snapshot events.

Published to ``onex.evt.linear.snapshot.v1`` by the Linear snapshot effect.
This is the Core-layer view: a superset of ``ContractLinearSnapshotEvent``
from omnibase_spi.

Topic: ``onex.evt.linear.snapshot.v1``
Partition key: ``snapshot_id``
"""

from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict, Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelLinearSnapshotEvent", "TOPIC_LINEAR_SNAPSHOT_EVENT"]

TOPIC_LINEAR_SNAPSHOT_EVENT = "onex.evt.linear.snapshot.v1"


class ModelLinearSnapshotEvent(ModelRuntimeEventBase):
    """Core event model for a Linear snapshot event.

    Published to ``onex.evt.linear.snapshot.v1`` after the Linear snapshot
    effect polls the Linear workspace.

    All fields from ``ContractLinearSnapshotEvent`` (omnibase_spi) must be
    present here (SPI contract fields ⊆ Core model fields invariant).

    Attributes:
        event_type: Fully-qualified event type identifier; equals the topic name.
        snapshot_id: Globally-unique snapshot identifier (UUID4).
            Used as the Kafka partition key.
        workstreams: Linear workstream identifiers captured in this snapshot.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=False,
        from_attributes=True,
    )

    event_type: str = Field(
        default=TOPIC_LINEAR_SNAPSHOT_EVENT,
        description="Fully-qualified event type identifier; equals the topic name.",
    )
    snapshot_id: UUID = Field(
        ...,
        description=(
            "Globally-unique snapshot identifier (UUID4). "
            "Used as the Kafka partition key."
        ),
    )
    workstreams: list[str] = Field(
        default_factory=list,
        description="Linear workstream identifiers captured in this snapshot.",
    )
