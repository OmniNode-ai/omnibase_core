# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cutover Criterion Enum (OMN-12621).

Strongly typed gating conditions that must hold before a topic migration may
advance to ``CUTOVER``. These are the observable proofs that the new topic is
safe to make authoritative.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumCutoverCriterion(UtilStrValueHelper, str, Enum):
    """Conditions required before a migration may cut over.

    - ``OLD_TOPIC_DRAINED``: the old topic has no un-consumed lag for the old
      consumer group (drain-proof gate satisfied).
    - ``NEW_TOPIC_CONSUMER_HEALTHY``: the new consumer group is live and
      committing offsets on the new topic.
    - ``COMPATIBILITY_WINDOW_ELAPSED``: the declared compatibility window has
      fully elapsed.
    - ``DUAL_WRITE_VERIFIED``: producers are confirmed writing to both topics
      with matching payload counts.
    - ``SCHEMA_PARITY_VERIFIED``: the new topic's event schema_version satisfies
      consumer compatibility (no unhandled breaking delta).
    """

    OLD_TOPIC_DRAINED = "old_topic_drained"
    NEW_TOPIC_CONSUMER_HEALTHY = "new_topic_consumer_healthy"
    COMPATIBILITY_WINDOW_ELAPSED = "compatibility_window_elapsed"
    DUAL_WRITE_VERIFIED = "dual_write_verified"
    SCHEMA_PARITY_VERIFIED = "schema_parity_verified"


__all__ = ["EnumCutoverCriterion"]
