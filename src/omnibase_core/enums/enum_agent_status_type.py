#!/usr/bin/env python3
"""
Agent Status Type Enum.

Strongly-typed enumeration for agent status types.
"""

from enum import Enum, unique


@unique
class EnumAgentStatusType(str, Enum):
    """Agent status enumeration."""

    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    TERMINATING = "terminating"
    STARTING = "starting"
    SUSPENDED = "suspended"
