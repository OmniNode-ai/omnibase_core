#!/usr/bin/env python3
"""
Agent Status Type Enum.

Strongly-typed enumeration for agent status types.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAgentStatusType(StrValueHelper, str, Enum):
    """Agent status enumeration."""

    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    TERMINATING = "terminating"
    STARTING = "starting"
    SUSPENDED = "suspended"


__all__ = ["EnumAgentStatusType"]
