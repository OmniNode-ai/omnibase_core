#!/usr/bin/env python3
"""
Workflow Priority Enumeration
Defines valid priority levels for AI workflow execution
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumWorkflowPriority(StrValueHelper, str, Enum):
    """Priority levels for workflow execution"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


__all__ = ["EnumWorkflowPriority"]
