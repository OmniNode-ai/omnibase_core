# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Allowed mechanical check types for task contract DoD verification."""

from enum import Enum


class EnumCheckType(str, Enum):
    """Allowed mechanical check types. Enum-constrained to prevent typo drift."""

    COMMAND_EXIT_0 = "command_exit_0"
    FILE_EXISTS = "file_exists"
    GREP_ABSENT = "grep_absent"
    GREP_PRESENT = "grep_present"
