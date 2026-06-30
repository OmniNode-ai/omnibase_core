# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for UI action-gate risk/commit enums (OMN-13131, ADR D2).

These enums give the UI-platform action-gate fields (risk_level, commit_level)
a canonical, strongly-typed home in core. They are scoped to the UI platform
under ``omnibase_core.enums.ui`` and are intentionally distinct from the
domain-scoped routing/overseer ``EnumRiskLevel`` definitions.
"""

from enum import StrEnum

import pytest


@pytest.mark.unit
class TestEnumRiskLevel:
    """Tests for the UI action-gate EnumRiskLevel."""

    def test_canonical_location(self) -> None:
        """EnumRiskLevel must live under omnibase_core.enums.ui."""
        from omnibase_core.enums.ui import EnumRiskLevel
        from omnibase_core.enums.ui.enum_risk_level import (
            EnumRiskLevel as EnumRiskLevelDirect,
        )

        assert EnumRiskLevel is EnumRiskLevelDirect

    def test_is_str_enum(self) -> None:
        """EnumRiskLevel is a StrEnum for cross-process wire safety."""
        from omnibase_core.enums.ui import EnumRiskLevel

        assert issubclass(EnumRiskLevel, StrEnum)

    def test_members(self) -> None:
        """EnumRiskLevel exposes the ordered low->critical risk axis."""
        from omnibase_core.enums.ui import EnumRiskLevel

        assert EnumRiskLevel.LOW.value == "low"
        assert EnumRiskLevel.MEDIUM.value == "medium"
        assert EnumRiskLevel.HIGH.value == "high"
        assert EnumRiskLevel.CRITICAL.value == "critical"
        assert {m.value for m in EnumRiskLevel} == {
            "low",
            "medium",
            "high",
            "critical",
        }


@pytest.mark.unit
class TestEnumCommitLevel:
    """Tests for the UI action-gate EnumCommitLevel."""

    def test_canonical_location(self) -> None:
        """EnumCommitLevel must live under omnibase_core.enums.ui."""
        from omnibase_core.enums.ui import EnumCommitLevel
        from omnibase_core.enums.ui.enum_commit_level import (
            EnumCommitLevel as EnumCommitLevelDirect,
        )

        assert EnumCommitLevel is EnumCommitLevelDirect

    def test_is_str_enum(self) -> None:
        """EnumCommitLevel is a StrEnum for cross-process wire safety."""
        from omnibase_core.enums.ui import EnumCommitLevel

        assert issubclass(EnumCommitLevel, StrEnum)

    def test_members(self) -> None:
        """EnumCommitLevel exposes the read-only -> irreversible commit axis."""
        from omnibase_core.enums.ui import EnumCommitLevel

        assert EnumCommitLevel.READ_ONLY.value == "read_only"
        assert EnumCommitLevel.REVERSIBLE.value == "reversible"
        assert EnumCommitLevel.IRREVERSIBLE.value == "irreversible"
        assert {m.value for m in EnumCommitLevel} == {
            "read_only",
            "reversible",
            "irreversible",
        }
