# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Activation decay for hybrid retrieval (OMN-16765, step 4).

Recency modulation: a document that was relevant and *recently touched*
outranks an equally-similar stale one.

Two things about the shape of this, both settled rather than invented here:

* **Decay is multiplicative and applied AFTER fusion**, as a modulation on the
  fused score — not as a third ranked list inside the fusion. That ordering
  comes from the architecture plan's §4.2 composed read path.
* **It reads the freshest timestamp the model actually carries.** The plan
  specifies ``max(created_at, last_accessed_at)``, but ``last_accessed_at`` is
  not reachable everywhere: the retrieval path returns ``ModelMemorySnapshot``,
  which is frozen, lives in ``omnibase_core``, and carries ``created_at`` only.
  Rather than plumb a field into a frozen core model speculatively, this
  degrades: where ``last_accessed_at`` exists the max applies, where it does not
  the function falls back to ``created_at`` alone.

  Note the fallback is needed per *instance*, not merely per model —
  ``ModelMemoryItem.last_accessed_at`` and ``ModelMemoryData.last_accessed_at``
  are both ``datetime | None``, so a model that declares the field can still
  present nothing for a given record.

Whether the ``created_at``-only path measurably costs ranking quality is a
question to answer with the fixture harness, not by assumption. Until that
delta is measured, no cross-repo change to the core model is justified.

.. versionadded:: 0.18.0
    Initial implementation for OMN-16765 step 4.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

__all__ = [
    "DECAY_LAMBDA_PER_DAY",
    "STALE_ACTIVATION_THRESHOLD",
    "activation_decay",
    "freshest_timestamp",
    "is_stale",
]

DECAY_LAMBDA_PER_DAY = 0.015
"""Decay constant, per day, for ``A(t) = A_0 * exp(-lambda * dt)``.

Unchanged from the value already live in
``node_agent_learning_retrieval_effect.handlers.handler_agent_learning_retrieval``
so the two paths cannot drift apart. Taken as-is rather than retuned — there is
no evidence in this repository that would justify moving it, and moving it
without evidence is worse than keeping a documented constant.

The actual curve: **0.900 at one week, 0.657 at four weeks, 0.600 at ~34
days**. This was mis-stated as "~60% at 4 weeks" in
``handler_agent_learning_retrieval.py`` — off by about six points, since 0.600
is a 34-day figure. Corrected there, and its tests now pin exact values rather
than the wide bands that let the error survive (``0.60 < score < 0.72``
contains both the true value and the wrong one, so it could never fail).

**The architecture plan's §2.3 still carries the same wrong claim** ("a
4-week-old learning scores 0.6x"). That doc is outside this repository, so it
is reported rather than fixed here.
"""

STALE_ACTIVATION_THRESHOLD = 0.3
"""Below this activation score a memory is considered stale.

From the plan's §5 Phase 2. Exposed here because ranking and the lifecycle
orchestrator must agree on what "stale" means; two independently chosen
thresholds would let a document rank as fresh while the lifecycle treats it as
stale.
"""


def freshest_timestamp(
    created_at: datetime,
    last_accessed_at: datetime | None = None,
) -> datetime:
    """Return the most recent timestamp available for a record.

    Args:
        created_at: When the record was created. Always present.
        last_accessed_at: When it was last read, if the model carries the field
            and the record has a value for it.

    Returns:
        ``max(created_at, last_accessed_at)`` when both are available,
        ``created_at`` otherwise.

    A ``last_accessed_at`` *older* than ``created_at`` is possible in principle
    — clock skew, or a backfill that stamped access times independently — so
    this takes the max rather than preferring ``last_accessed_at`` whenever it
    is non-null. Preferring it would let a bad backfill silently age every
    record.
    """
    if last_accessed_at is None:
        return created_at
    return max(created_at, last_accessed_at)


def activation_decay(
    created_at: datetime,
    last_accessed_at: datetime | None = None,
    *,
    now: datetime,
) -> float:
    """Exponential activation decay against the freshest available timestamp.

    Args:
        created_at: When the record was created.
        last_accessed_at: Last read time, or None where unavailable.
        now: The reference time. Required and injected rather than read from
            the clock, so the value is reproducible in a test and identical
            across every result in one response.

    Returns:
        A multiplier in ``(0.0, 1.0]``. Exactly 1.0 for a record touched now,
        approaching 0 as it ages. Never negative and never above 1.0.

    A record whose freshest timestamp is in the future scores 1.0 rather than
    above it: future timestamps come from clock skew, and letting them amplify
    a score would make skew a ranking advantage.
    """
    reference = freshest_timestamp(created_at, last_accessed_at)
    days_old = max(0.0, (now - reference).total_seconds() / 86400)
    return math.exp(-DECAY_LAMBDA_PER_DAY * days_old)


def is_stale(activation_score: float) -> bool:
    """Whether an activation score has decayed past the stale threshold."""
    return activation_score < STALE_ACTIVATION_THRESHOLD
