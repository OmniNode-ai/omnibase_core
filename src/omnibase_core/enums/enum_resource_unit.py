# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Resource Unit Enumeration.

Defines the units of measurement for resource usage metrics
(CPU, memory, disk, network, etc.).
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumResourceUnit(UtilStrValueHelper, str, Enum):
    """Resource usage unit enumeration."""

    PERCENTAGE = "percentage"
    BYTES = "bytes"
    MBPS = "mbps"
    IOPS = "iops"
    OTHER = "other"


__all__ = ["EnumResourceUnit"]
