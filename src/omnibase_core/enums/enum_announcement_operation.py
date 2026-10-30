# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Operation carried by a node announcement (OMN-21589)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumAnnouncementOperation(UtilStrValueHelper, str, Enum):
    """What an announcement tells the catalog about one contract.

    Attributes:
        ANNOUNCE: The contract is installed at the announced content hash.
        WITHDRAW: The contract's package is gone; the name stops being startable.
    """

    ANNOUNCE = "announce"
    WITHDRAW = "withdraw"
