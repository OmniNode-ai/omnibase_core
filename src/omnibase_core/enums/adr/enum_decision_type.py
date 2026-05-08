# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Decision type enum for ADR extraction (OMN-10691)."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDecisionType(StrValueHelper, str, Enum):
    """Classifies the type of architectural decision extracted."""

    ARCHITECTURE_DECISION = "architecture_decision"
    ARCHITECTURE_PIVOT = "architecture_pivot"
    DOCTRINE_FORMATION = "doctrine_formation"
    OPERATIONAL_LESSON = "operational_lesson"
    SUPERSESSION = "supersession"
    REJECTED_APPROACH = "rejected_approach"
