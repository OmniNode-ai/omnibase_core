# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Customer tier classification for subscription levels."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumCustomerTier(UtilStrValueHelper, str, Enum):
    """Customer subscription tier classification.

    Used to categorize customers by their subscription level for
    prioritization, feature access, and support routing decisions.
    """

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


__all__ = ["EnumCustomerTier"]
