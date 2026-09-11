# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Closed GitHub diff-status vocabulary for package-only deploy bindings."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumPackageOnlyManifestStatus(str, Enum):
    """GitHub pull-request file statuses admitted into a typed manifest."""

    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    RENAMED = "renamed"
    COPIED = "copied"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


__all__ = ["EnumPackageOnlyManifestStatus"]
