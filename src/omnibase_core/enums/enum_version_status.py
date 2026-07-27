# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Version Status Enums.

Version lifecycle status values.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumVersionStatus(UtilStrValueHelper, str, Enum):
    """Version lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    ALPHA = "alpha"
    END_OF_LIFE = "end_of_life"


__all__ = ["EnumVersionStatus"]
