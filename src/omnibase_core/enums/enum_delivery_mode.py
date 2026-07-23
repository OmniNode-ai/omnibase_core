# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for event delivery modes.

Defines the available modes for event delivery in the ONEX system.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumDeliveryMode(UtilStrValueHelper, str, Enum):
    """
    Enumeration of event delivery modes.

    These modes determine how events are delivered from CLI to nodes.
    """

    DIRECT = "direct"
    INMEMORY = "inmemory"


__all__ = ["EnumDeliveryMode"]
