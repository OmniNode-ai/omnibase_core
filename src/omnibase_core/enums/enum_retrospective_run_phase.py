# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Phase of a retrospective run in the reducer's state (OMN-21627)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumRetrospectiveRunPhase(UtilStrValueHelper, str, Enum):
    """States of the retrospective run state machine, as projected.

    Attributes:
        OPEN: The run is open and its cohort window is recorded.
        COLLECTED: An immutable evidence snapshot exists.
        EVALUATED: Every experiment carries a verdict.
        DIGESTED: The digest is recorded.
    """

    OPEN = "open"
    COLLECTED = "collected"
    EVALUATED = "evaluated"
    DIGESTED = "digested"
