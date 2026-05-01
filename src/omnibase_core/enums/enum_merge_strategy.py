# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Merge strategy enumeration for GitHub PR lifecycle management.

Defines the available merge strategies used by the merge sweep system
and auto-merge skill.

See Also:
    - OMN-7260: Merge strategy detection and conflict handling
    - :class:`MergeStrategyDetector`: Resolves strategy per repository

.. versionadded:: 0.40.0
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumMergeStrategy(str, Enum):
    """Strategy for merging a PR via ``gh pr merge``.

    Attributes:
        MERGE_QUEUE: Repository uses a GitHub merge queue. The queue
            controls the merge method, so only ``--auto`` is needed.
        SQUASH_AUTO: No merge queue; use ``--squash --auto`` directly.
    """

    MERGE_QUEUE = "merge_queue"
    SQUASH_AUTO = "squash_auto"


# TODO(OMN-7260): Remove alias once all consumers migrated to EnumMergeStrategy.
MergeStrategy = EnumMergeStrategy
