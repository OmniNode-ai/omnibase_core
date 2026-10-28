# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery resolved kind values."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumDeliveryResolvedKind"]


@unique
class EnumDeliveryResolvedKind(UtilStrValueHelper, str, Enum):
    """Declared delivery resolved kind."""

    TAG = "tag"
    BRANCH = "branch"
    COMMIT = "commit"
    VERSION = "version"
    UNRESOLVED = "unresolved"
