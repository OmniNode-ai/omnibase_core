# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed cross-repository proof kinds declared by goal manifests."""

from enum import StrEnum


class EnumGoalProofKind(StrEnum):
    """Evidence class referenced by one protected dependency pin."""

    COMMIT_CHECK = "commit_check"
    MERGE_GROUP_CHECK = "merge_group_check"
    MERGE_RESULT = "merge_result"
    DEPLOYMENT = "deployment"
    PUBLISHED_PASS = "published_pass"
    TERMINAL = "terminal"


__all__ = ["EnumGoalProofKind"]
