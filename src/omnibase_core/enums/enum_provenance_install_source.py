# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Provenance Install Source Enum.

How the emitter's code was installed.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumProvenanceInstallSource(UtilStrValueHelper, str, Enum):
    """Install source of the emitter's code."""

    TAG = "tag"
    BRANCH = "branch"
    WORKTREE = "worktree"
    HAND = "hand"


__all__: list[str] = ["EnumProvenanceInstallSource"]
