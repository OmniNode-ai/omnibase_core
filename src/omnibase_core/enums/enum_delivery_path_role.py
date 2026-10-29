# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery path role values."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumDeliveryPathRole"]


@unique
class EnumDeliveryPathRole(UtilStrValueHelper, str, Enum):
    """Declared delivery path role."""

    CONTINUOUS = "continuous"
    PRE_PR = "pre_pr"
    REQUIRED_GATE = "required_gate"
    DEPENDENCY = "dependency"
