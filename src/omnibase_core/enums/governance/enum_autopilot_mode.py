# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Autopilot Mode Enum.

Closed set of operating modes for the autopilot close-out loop.
"""

from enum import Enum, unique


@unique
class EnumAutopilotMode(str, Enum):
    """Operating modes for the autopilot pipeline.

    - CLOSE_OUT: autopilot is merging, closing, and triaging completed work
    - BUILD: autopilot is dispatching build workers for new tickets
    """

    CLOSE_OUT = "close_out"
    """Merge, close, and triage completed work."""

    BUILD = "build"
    """Dispatch build workers for new or In Progress tickets."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
