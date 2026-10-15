# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context factor enum for context pack pipeline."""

from __future__ import annotations

from enum import Enum


class EnumContextFactor(str, Enum):
    """Factor type used to categorize a context chunk in a context pack."""

    GOLDEN_CHAIN = "golden_chain"
    EXEMPLAR = "exemplar"
    LOCAL_FAILURES = "local_failures"
    ARCHITECTURE_PATTERNS = "architecture_patterns"
    CLAUDE_MD = "claude_md"

    # Session factors (OMN-18531, plan task TA.2). Append-only: never reorder.
    OPERATOR_RULINGS = "operator_rulings"
    OPERATOR_WORDS_UNRECORDED = "operator_words_unrecorded"
    ORCHESTRATION_STATE = "orchestration_state"
    OPEN_WORK = "open_work"
    REPO_STATE = "repo_state"
    CONVERSATION_TAIL = "conversation_tail"

    # Tier factors. Patterns and exemplars reuse ARCHITECTURE_PATTERNS and EXEMPLAR.
    LANE_RULES = "lane_rules"
    INVARIANTS = "invariants"
    ADRS = "adrs"
    CANONICAL_SHAPES = "canonical_shapes"
    PLAN_EXCERPTS = "plan_excerpts"
    SESSION_GOAL = "session_goal"
    CAPABILITY_DIGEST = "capability_digest"
    TRANSCRIPT_EXTRACTS = "transcript_extracts"
    TAIL_SUMMARY = "tail_summary"


__all__ = [
    "EnumContextFactor",
]
