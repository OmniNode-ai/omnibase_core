# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Triage state enum for GitHub pull request classification."""

from enum import Enum


class EnumTriageState(str, Enum):
    """Triage classification of a GitHub pull request."""

    DRAFT = "draft"
    STALE = "stale"
    CI_FAILING = "ci_failing"
    CHANGES_REQUESTED = "changes_requested"
    READY_TO_MERGE = "ready_to_merge"
    APPROVED_PENDING_CI = "approved_pending_ci"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


__all__ = ["EnumTriageState"]
