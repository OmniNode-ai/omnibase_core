# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumContextFactor (OMN-18531, plan task TA.2).

The five original members keep their positions; the six session factors and the
nine tier factors are appended after them, in that order, with string values
equal to their lower-case names.
"""

import pytest

from omnibase_core.enums.enum_context_factor import EnumContextFactor

EXISTING_FACTORS = (
    "GOLDEN_CHAIN",
    "EXEMPLAR",
    "LOCAL_FAILURES",
    "ARCHITECTURE_PATTERNS",
    "CLAUDE_MD",
)
SESSION_FACTORS = (
    "OPERATOR_RULINGS",
    "OPERATOR_WORDS_UNRECORDED",
    "ORCHESTRATION_STATE",
    "OPEN_WORK",
    "REPO_STATE",
    "CONVERSATION_TAIL",
)
TIER_FACTORS = (
    "LANE_RULES",
    "INVARIANTS",
    "ADRS",
    "CANONICAL_SHAPES",
    "PLAN_EXCERPTS",
    "SESSION_GOAL",
    "CAPABILITY_DIGEST",
    "TRANSCRIPT_EXTRACTS",
    "TAIL_SUMMARY",
)
EXPECTED_ORDER = EXISTING_FACTORS + SESSION_FACTORS + TIER_FACTORS


@pytest.mark.unit
class TestEnumContextFactor:
    def test_members_in_order(self) -> None:
        """Existing five, then the six session factors, then the nine tier factors."""
        assert [m.name for m in EnumContextFactor] == list(EXPECTED_ORDER)

    def test_exactly_twenty_members(self) -> None:
        assert len(list(EnumContextFactor)) == 20

    def test_existing_members_keep_their_positions(self) -> None:
        members = list(EnumContextFactor)
        for index, name in enumerate(EXISTING_FACTORS):
            assert members[index].name == name

    @pytest.mark.parametrize("name", EXPECTED_ORDER)
    def test_value_is_lower_case_name(self, name: str) -> None:
        assert EnumContextFactor[name].value == name.lower()

    def test_no_member_duplicates_patterns_or_exemplars(self) -> None:
        """Patterns and exemplars reuse ARCHITECTURE_PATTERNS and EXEMPLAR."""
        added = [m.name for m in EnumContextFactor][len(EXISTING_FACTORS) :]
        assert added == list(SESSION_FACTORS + TIER_FACTORS)
        assert not [n for n in added if "PATTERN" in n or "EXEMPLAR" in n]
