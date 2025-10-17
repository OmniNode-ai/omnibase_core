#!/usr/bin/env python3
"""
Event and logging-related enums for ONEX systems.

Defines log levels for ONEX logging systems.
"""

from enum import Enum


class EnumEvents(str, Enum):
    """
    Logging level enumeration for ONEX logging systems.

    Standard log levels for consistent logging across ONEX components.
    """

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
