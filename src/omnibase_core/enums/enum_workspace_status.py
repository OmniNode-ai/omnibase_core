#!/usr/bin/env python3
"""
Enum for Workspace Status.

Defines the valid states in the workspace lifecycle.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumWorkspaceStatus(StrValueHelper, str, Enum):
    """Workspace lifecycle states."""

    CREATING = "creating"
    READY = "ready"
    ACTIVE = "active"
    MERGING = "merging"
    CLEANUP = "cleanup"
    FAILED = "failed"


__all__ = ["EnumWorkspaceStatus"]
