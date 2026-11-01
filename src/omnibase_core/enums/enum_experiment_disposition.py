# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Disposition of an experiment after a retrospective (OMN-21627)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentDisposition(UtilStrValueHelper, str, Enum):
    """What the approved progression rules make of an experiment's verdict.

    Attributes:
        KEEP: Keep the change.
        REVISE: Revise the change and measure again.
        STOP: Stop the experiment.
        EXTEND: Extend the window because evidence is immature.
    """

    KEEP = "keep"
    REVISE = "revise"
    STOP = "stop"
    EXTEND = "extend"
