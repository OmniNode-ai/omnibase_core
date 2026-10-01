# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed subject identities used by goal evidence."""

from enum import StrEnum


class EnumGoalSubjectKind(StrEnum):
    """Subject domain whose exact identity a goal observation binds."""

    COMMIT = "commit"
    MERGE_GROUP = "merge_group"
    DEPLOYMENT = "deployment"


__all__ = ["EnumGoalSubjectKind"]
