# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Case transformation modes for contract-driven NodeCompute.

This module defines the case modes available for CASE_CONVERSION transformations.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumCaseMode(UtilStrValueHelper, str, Enum):
    """
    Case transformation modes.

    Attributes:
        UPPER: Convert text to uppercase.
        LOWER: Convert text to lowercase.
        TITLE: Convert text to titlecase.
    """

    UPPER = "uppercase"
    LOWER = "lowercase"
    TITLE = "titlecase"


__all__ = ["EnumCaseMode"]
