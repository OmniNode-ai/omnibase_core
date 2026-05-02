# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""GitHub integration adapters for merge orchestration.

Provides merge strategy detection, queue-based PR lifecycle management,
and rebase conflict handling.
"""

from __future__ import annotations

from omnibase_core.adapters.github_merge_queue_adapter import GitHubMergeQueueAdapter
from omnibase_core.adapters.merge_strategy_detector import MergeStrategyDetector
from omnibase_core.adapters.rebase_handler import RebaseResult, attempt_rebase
from omnibase_core.enums.enum_merge_strategy import EnumMergeStrategy

__all__ = [
    "GitHubMergeQueueAdapter",
    "EnumMergeStrategy",
    "MergeStrategyDetector",
    "RebaseResult",
    "attempt_rebase",
]
