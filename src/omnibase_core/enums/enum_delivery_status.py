# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery status values."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumDeliveryStatus"]


@unique
class EnumDeliveryStatus(UtilStrValueHelper, str, Enum):
    """Declared delivery status."""

    ALLOWED = "allowed"
    REFUSED = "refused"
    TAG_MOVED = "tag_moved"
    UNDECLARED = "undeclared"
    BLOCKED = "blocked"
