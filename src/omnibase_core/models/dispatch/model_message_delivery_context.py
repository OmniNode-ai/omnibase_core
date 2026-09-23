# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Where a message was delivered from, as distinct from what the event says.

OMN-18920, step 1 of the OMN-18918 chain, under the operator ruling of
2026-09-20 selecting option C3.

WHY THIS IS NOT A FIELD ON THE ENVELOPE
---------------------------------------
``ModelEventEnvelope`` is the PRODUCER's truth: what happened, when the
producer says it happened, who it belongs to. A partition and an offset are
facts about a **delivery** — where the broker happened to put this copy of
that event, and where this consumer happened to read it. The same event
redelivered at another offset is the same event, so hanging coordinates on
the envelope would quietly make two copies of one event look like two
events. Threading consumer-side facts through producer-set message headers
would break the same identity less visibly. Hence a separate model, passed
beside the envelope rather than inside it.

WHY IT LIVES IN CORE
--------------------
Operating Rule 7: protocol I/O types that the spi protocols reference belong
in core, so spi can import them without a circular package dependency.
``ProtocolDispatchEngine`` already imports its sibling
``ModelDispatchResult`` from this very package, and step 2 gives that
protocol an optional parameter of this type.
``docs/architecture/layering-exceptions.yaml`` was read first and declares
no exception covering the dispatch family, so the default placement holds.

WHAT IT IS FOR
--------------
Every in-process projection writer builds its ``MessageMeta`` from
``_partition``/``_offset``; the runtime injects neither, so every snapshot
delta is published at offset 0. ``SnapshotCache`` refuses a delta whose
offset does not exceed the one it already holds for that key, and a constant
never exceeds itself — so every delta after the first for a given key is
discarded as a replay. First writer wins forever, at zero consumer lag, with
a green readiness endpoint. Measured on the ``.201`` dev lane 2026-09-20: a
trace subscribed to ``onex.snapshot.projection.runner-fleet.v1`` alone
replayed to the end of the topic and still served rows ten hours old. The
full trace is on OMN-18905.

This step is INERT. Nothing imports this model until step 2.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelMessageDeliveryContext(BaseModel):
    """One message's delivery coordinates, as the consumer observed them.

    Frozen: a delivery already happened, so nothing downstream has any
    business revising where it came from.

    Example:
        >>> context = ModelMessageDeliveryContext(
        ...     topic="onex.evt.omnibase-infra.runner-fleet.v1",
        ...     partition=0,
        ...     offset=16698,
        ... )
        >>> context.offset
        16698
        >>> context.broker_timestamp is None
        True
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    topic: str = Field(
        min_length=1,
        description=(
            "The topic this copy of the message was read from. Carried "
            "alongside the coordinates because an offset is only meaningful "
            "against a topic and partition, never on its own."
        ),
    )
    partition: int = Field(
        ge=0,
        description=(
            "The partition this copy was read from. Non-negative by "
            "definition; refused rather than accepted as a sentinel, because "
            "a silently-tolerated -1 is the shape a 'no value' marker takes "
            "the first time somebody needs one, and a sentinel here reads "
            "downstream as a real coordinate."
        ),
    )
    offset: int = Field(
        ge=0,
        description=(
            "The offset this copy was read at. This is the ordering "
            "authority a projection uses to tell a newer fact from a "
            "redelivery of an older one, which is why it is refused rather "
            "than defaulted when unknown."
        ),
    )
    broker_timestamp: datetime | None = Field(
        default=None,
        description=(
            "The broker-recorded time for this record, when the consume path "
            "has one. Optional and NEVER defaulted to a clock reading: an "
            "absent broker time must stay distinguishable from a real one, "
            "or a consumer ends up reading the runtime's own wall clock as a "
            "broker fact. The same reason `_envelope_timestamp` is injected "
            "only when the producer actually recorded one."
        ),
    )
