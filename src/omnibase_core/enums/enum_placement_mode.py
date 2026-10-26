# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime placement modes declared by node contracts."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumPlacementMode(UtilStrValueHelper, str, Enum):
    """Whether every runtime or only the elected primary handles a node."""

    ANY = "any"
    PRIMARY = "primary"
