#!/usr/bin/env python3
"""
Execution-related enums for ONEX operations.

Defines execution modes and operation status values for
ONEX system operations and workflow management.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumExecutionMode(Enum):
    """
    Execution modes for CLI commands and node operations.

    Defines how commands are executed and routed through the ONEX system.
    """

    DIRECT = "direct"
    INMEMORY = "inmemory"


@unique
class EnumOperationStatus(StrValueHelper, str, Enum):
    """
    Operation status values for service operations.

    Provides standardized status values for service manager operations.
    """

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    PENDING = "pending"
    TIMEOUT = "timeout"
