# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hold-Block Enum (OMN-16177, typed work ledger).

The actions a typed hold (``work.hold.placed``) stops. A hold names at least
one. The checker answers "is this action held for this PR, repo, surface or
lane" from these members alone; it never reads the hold's prose.
"""

from enum import StrEnum, unique


@unique
class EnumHoldBlock(StrEnum):
    """Which action a hold blocks."""

    MERGE = "merge"
    """Merging a pull request in scope."""

    ARM = "arm"
    """Arming auto-merge on a pull request in scope."""

    DISPATCH = "dispatch"
    """Dispatching a lane onto work in scope."""

    DEPLOY = "deploy"
    """Deploying to, or otherwise mutating, a surface in scope."""


__all__: list[str] = ["EnumHoldBlock"]
