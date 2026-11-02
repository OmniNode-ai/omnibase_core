# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Champion decision computed from an experiment verdict (OMN-22001)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumChampionDecision(UtilStrValueHelper, str, Enum):
    """The MASS champion decision. It is computed from a verdict and is not part of one.

    Attributes:
        PROMOTE: The challenger replaces the champion.
        RETAIN: The champion stays.
        REJECT: The challenger is rejected.
    """

    PROMOTE = "promote"
    RETAIN = "retain"
    REJECT = "reject"
