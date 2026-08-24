# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-Event Kind Enum (OMN-16177).

The five work-event kinds that make the rolling work ledger a projection over
the ordinary hook-captured event stream rather than a hand-appended markdown
file. These are ordinary event types in the existing ``onex.evt.omniclaude.*``
producer namespace — not a new topic family.

Values are the registry ``event_type`` keys verbatim, so
``EnumWorkEventKind.CLAIM_REQUESTED.value`` is exactly the key the emit
registry (``node_emit_daemon/registries/topics.yaml``) declares.
"""

from enum import StrEnum, unique


@unique
class EnumWorkEventKind(StrEnum):
    """Work-event kinds, split across two partition-key domains.

    ``CLAIM_REQUESTED`` / ``CLAIM_RELEASED`` are the arbitration domain and
    partition on ``ticket_id``. The remaining three are the narrative domain
    and partition on ``actor_key``. See
    ``omnibase_core.models.events.work.WORK_EVENT_PARTITION_KEY_FIELDS``.
    """

    CLAIM_REQUESTED = "work.claim.requested"
    """A claimant asks to own a ticket. Arbitrated by partition offset order."""

    CLAIM_RELEASED = "work.claim.released"
    """A claimant gives up ownership of a ticket it previously requested."""

    RESULT_RECORDED = "work.result.recorded"
    """An outcome with structured PR/OCC citations and quantitative claims."""

    RULING_RECORDED = "work.ruling.recorded"
    """An operator ruling, recorded verbatim against the actor that heard it."""

    CORRECTION_RECORDED = "work.correction.recorded"
    """A correction to an earlier record. Append-only; never an edit in place."""


__all__: list[str] = ["EnumWorkEventKind"]
