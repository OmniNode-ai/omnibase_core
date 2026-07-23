# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for node status values.

Defines the possible status values for ONEX nodes.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumNodeStatus(UtilStrValueHelper, str, Enum):
    """
    Enumeration of node status values.

    These values represent the operational state of ONEX nodes.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
