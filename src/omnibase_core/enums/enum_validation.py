#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Validation-related enums for ONEX validation systems.

Defines validation levels for ONEX validation systems.

Note (OMN-1311):
    EnumErrorSeverity was removed in favor of the canonical EnumSeverity.
    Import severity from: omnibase_core.enums.enum_severity import EnumSeverity
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationLevel(StrValueHelper, str, Enum):
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
