# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Triage state enum for GitHub pull request classification.

.. versionadded:: 0.19.0  (OMN-2655)
"""

from __future__ import annotations

from enum import Enum

__all__ = ["EnumGitHubPRTriageState"]


class EnumGitHubPRTriageState(str, Enum):
    """Triage classification of a GitHub pull request."""

    DRAFT = "draft"
    STALE = "stale"
    CI_FAILING = "ci_failing"
    CHANGES_REQUESTED = "changes_requested"
    READY_TO_MERGE = "ready_to_merge"
    APPROVED_PENDING_CI = "approved_pending_ci"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
