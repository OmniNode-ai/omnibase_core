# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Segment type enum for ADR document segmentation (OMN-10691)."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSegmentType(StrValueHelper, str, Enum):
    """Classifies the semantic role of a document segment."""

    DECISION = "decision"
    CRITIQUE = "critique"
    PROPOSAL = "proposal"
    MIGRATION = "migration"
    INVARIANT = "invariant"
    FAILURE_ANALYSIS = "failure_analysis"
    OPERATIONAL_CONCERN = "operational_concern"
    HYPOTHESIS = "hypothesis"
    DOCTRINE_FORMATION = "doctrine_formation"
    IMPLEMENTATION_DETAIL = "implementation_detail"
    ARCHITECTURAL_RISK = "architectural_risk"
    NON_DECISION = "non_decision"
    BACKGROUND = "background"
    UNKNOWN = "unknown"
