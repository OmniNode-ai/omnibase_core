#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Validation-related enums for ONEX validation systems.

Defines validation levels for ONEX validation and error handling systems.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumValidationLevel(UtilStrValueHelper, str, Enum):
    """
    Validation levels for pipeline data integrity.

    Defines the validation levels for pipeline data integrity checking
    in the metadata processing pipeline.
    """

    BASIC = "BASIC"
    STANDARD = "STANDARD"
    COMPREHENSIVE = "COMPREHENSIVE"
    PARANOID = "PARANOID"


__all__ = ["EnumValidationLevel"]
