# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a contract hot-load request or record does to one contract name (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractHotloadOperation(UtilStrValueHelper, str, Enum):
    """What a contract hot-load request or record does to one contract name."""

    LOAD = "load"
    REMOVE = "remove"
