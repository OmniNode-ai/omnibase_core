# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-message delivery disposition for the unified runtime dispatch loop.

Net-new for the single-runtime / transport-via-DI unification (epic OMN-14717,
ticket OMN-14747; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` section
(d.1)). ``RuntimeDispatch._dispatch_one`` returns exactly one of these and NEVER
raises — the disposition is the runtime's decision about a single message and drives
the per-partition contiguous-prefix commit policy (plan HOLE 1):

* ``COMMIT`` — the message was successfully terminalized; it extends the committable
  contiguous prefix for its partition.
* ``REDELIVER`` — a retryable failure; the message (and everything after it on the
  partition) must be redelivered. It STOPS the committable prefix at this message so
  a later message's commit cannot advance the high-water mark past it (the silent-loss
  bug HOLE 1 exists to prevent).
* ``DLQ`` — retries are exhausted (or the failure is terminal); the runtime sends a
  dead-letter copy (the durable at-least-once evidence) and then treats the message as
  committable so the partition can make progress.

This is distinct from :class:`~omnibase_core.enums.enum_delivery_mode.EnumDeliveryMode`
(``DIRECT``/``INMEMORY``), which selects how a CLI delivers an event to a node — an
unrelated concern.
"""

from enum import Enum, unique


@unique
class EnumDeliveryDisposition(str, Enum):
    """The runtime's per-message delivery decision (commit / redeliver / DLQ)."""

    COMMIT = "commit"
    REDELIVER = "redeliver"
    DLQ = "dlq"


__all__ = ["EnumDeliveryDisposition"]
