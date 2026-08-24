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
    - closed: PR was closed without merging
    """

    MERGED = "merged"
    """PR has been merged."""

    OPEN = "open"
    """PR is currently open."""

    CLOSED = "closed"
    """PR was closed without merging (OMN-16177).

    Added so a work-event citation can record an abandoned PR honestly. A
    closed-unmerged PR is real evidence about a lane's outcome; collapsing it
    into ``OPEN`` or omitting it would misreport the record.
    """

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
