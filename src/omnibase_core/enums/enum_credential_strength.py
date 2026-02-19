# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnumCredentialStrength: Enumeration of credential strength levels.

This enum defines the strength levels for credential assessment.
"""

from enum import Enum, unique


@unique
class EnumCredentialStrength(Enum):
    """Credential strength levels."""

    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    INVALID = "invalid"
