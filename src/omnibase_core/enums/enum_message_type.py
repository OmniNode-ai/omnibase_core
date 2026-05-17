# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumMessageType(UtilStrValueHelper, str, Enum):
    """Message categories for proper routing and handling."""

    COMMAND = "command"
    DATA = "data"
    NOTIFICATION = "notification"
    QUERY = "query"


__all__ = ["EnumMessageType"]
