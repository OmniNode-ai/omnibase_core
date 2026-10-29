# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Where a resident omnimarket validator lives (OMN-21503)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumValidatorInventoryKind(UtilStrValueHelper, str, Enum):
    """Kind of artifact an inventory entry names."""

    SCRIPT = "script"
    NODE = "node"
