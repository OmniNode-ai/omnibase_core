# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PR State Enum.

States for pull requests in daily close reports.
"""

from enum import Enum, unique


@unique
class EnumPRState(str, Enum):
    """States for pull requests.

    PR states:
    - merged: PR has been merged
    - open: PR is currently open
    """

    MERGED = "merged"
    """PR has been merged."""

    OPEN = "open"
    """PR is currently open."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
