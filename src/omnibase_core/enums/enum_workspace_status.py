#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for Workspace Status.

Defines the valid states in the workspace lifecycle.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumWorkspaceStatus(UtilStrValueHelper, str, Enum):
    """Workspace lifecycle states."""

    CREATING = "creating"
    READY = "ready"
    ACTIVE = "active"
    MERGING = "merging"
    CLEANUP = "cleanup"
    FAILED = "failed"


__all__ = ["EnumWorkspaceStatus"]
