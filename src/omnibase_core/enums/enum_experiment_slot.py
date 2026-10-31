# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Origin slot of a retrospective skill experiment (OMN-21627)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentSlot(UtilStrValueHelper, str, Enum):
    """The three origin-based candidate slots of the weekly retrospective.

    Attributes:
        R1: Verified team status experiment.
        R2: Verified full result relay experiment.
        R3: Approval-ready action packet experiment.
    """

    R1 = "r1"
    R2 = "r2"
    R3 = "r3"
