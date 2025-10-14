#!/usr/bin/env python3
"""
Workflow Priority Enumeration
Defines valid priority levels for AI workflow execution
"""

from enum import Enum


class EnumWorkflowPriority(str, Enum):
    """Priority levels for workflow execution"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
