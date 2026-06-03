# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Migration Phase Enum (OMN-12621).

Strongly typed lifecycle phases for a topic-migration contract. A migration
moves producers/consumers from an ``old`` topic (and consumer group) to a
``new`` topic during a bounded compatibility window, then cuts over.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumMigrationPhase(UtilStrValueHelper, str, Enum):
    """Lifecycle phases of a topic migration.

    Phases progress strictly forward:

    - ``PLANNED``: contract authored, no traffic moved yet.
    - ``DUAL_WRITE``: producers write to both old and new topics; consumers
      still read the old topic.
    - ``DUAL_READ``: consumers read both topics during the compatibility
      window; new consumers prefer the new topic.
    - ``CUTOVER``: new topic is authoritative; old topic is drained, not
      written. Gated by the drain-proof gate and cutover criteria.
    - ``COMPLETE``: old topic and old consumer group are decommissioned.
    """

    PLANNED = "planned"
    DUAL_WRITE = "dual_write"
    DUAL_READ = "dual_read"
    CUTOVER = "cutover"
    COMPLETE = "complete"


__all__ = ["EnumMigrationPhase"]
