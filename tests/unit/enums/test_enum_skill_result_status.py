# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumSkillResultStatus."""

from __future__ import annotations

import json

import pytest

from omnibase_core.enums.enum_skill_result_status import (
    EnumSkillResultStatus,
    SkillResultStatus,
)


@pytest.mark.unit
class TestEnumSkillResultStatus:
    """Tests for the canonical skill result status enum."""

    def test_canonical_values_exist(self) -> None:
        """All 9 canonical status values are present with correct string values."""
        assert EnumSkillResultStatus.SUCCESS.value == "success"
        assert EnumSkillResultStatus.PARTIAL.value == "partial"
        assert EnumSkillResultStatus.FAILED.value == "failed"
        assert EnumSkillResultStatus.ERROR.value == "error"
        assert EnumSkillResultStatus.BLOCKED.value == "blocked"
        assert EnumSkillResultStatus.SKIPPED.value == "skipped"
        assert EnumSkillResultStatus.DRY_RUN.value == "dry_run"
        assert EnumSkillResultStatus.PENDING.value == "pending"
        assert EnumSkillResultStatus.GATED.value == "gated"

    def test_exactly_nine_values(self) -> None:
        """The enum has exactly 9 members -- no more, no less."""
        assert len(EnumSkillResultStatus) == 9

    def test_is_terminal(self) -> None:
        """Terminal statuses = no further processing expected."""
        terminal = {
            EnumSkillResultStatus.SUCCESS,
            EnumSkillResultStatus.PARTIAL,
            EnumSkillResultStatus.FAILED,
            EnumSkillResultStatus.ERROR,
            EnumSkillResultStatus.SKIPPED,
            EnumSkillResultStatus.DRY_RUN,
        }
        non_terminal = {
            EnumSkillResultStatus.BLOCKED,
            EnumSkillResultStatus.PENDING,
            EnumSkillResultStatus.GATED,
        }
        for status in terminal:
            assert status.is_terminal, f"{status} should be terminal"
        for status in non_terminal:
            assert not status.is_terminal, f"{status} should NOT be terminal"

    def test_is_success_like(self) -> None:
        """Success-like = counts as positive outcome."""
        success_like = {
            EnumSkillResultStatus.SUCCESS,
            EnumSkillResultStatus.PARTIAL,
            EnumSkillResultStatus.DRY_RUN,
        }
        not_success_like = {
            EnumSkillResultStatus.FAILED,
            EnumSkillResultStatus.ERROR,
            EnumSkillResultStatus.BLOCKED,
            EnumSkillResultStatus.SKIPPED,
            EnumSkillResultStatus.PENDING,
            EnumSkillResultStatus.GATED,
        }
        for status in success_like:
            assert status.is_success_like, f"{status} should be success-like"
        for status in not_success_like:
            assert not status.is_success_like, f"{status} should NOT be success-like"

    def test_all_members_covered_by_terminal_check(self) -> None:
        """Every enum member returns a bool from is_terminal (no exceptions)."""
        for status in EnumSkillResultStatus:
            assert isinstance(status.is_terminal, bool)

    def test_all_members_covered_by_success_like_check(self) -> None:
        """Every enum member returns a bool from is_success_like (no exceptions)."""
        for status in EnumSkillResultStatus:
            assert isinstance(status.is_success_like, bool)

    def test_str_serialization(self) -> None:
        """str() returns the value string, suitable for JSON serialization."""
        assert str(EnumSkillResultStatus.SUCCESS) == "success"
        assert str(EnumSkillResultStatus.DRY_RUN) == "dry_run"

    def test_json_serialization(self) -> None:
        """Enum values serialize correctly in JSON payloads."""
        payload = {"status": EnumSkillResultStatus.FAILED}
        serialized = json.dumps(payload)
        assert '"failed"' in serialized

    def test_value_lookup(self) -> None:
        """Enum can be constructed from string values."""
        assert EnumSkillResultStatus("success") is EnumSkillResultStatus.SUCCESS
        assert EnumSkillResultStatus("dry_run") is EnumSkillResultStatus.DRY_RUN
        assert EnumSkillResultStatus("gated") is EnumSkillResultStatus.GATED

    def test_invalid_value_raises(self) -> None:
        """Constructing from an invalid string raises ValueError."""
        with pytest.raises(ValueError, match="'invalid'"):
            EnumSkillResultStatus("invalid")

    def test_alias_identity(self) -> None:
        """SkillResultStatus alias points to the same enum class."""
        assert SkillResultStatus is EnumSkillResultStatus

    def test_failed_vs_error_semantic_boundary(self) -> None:
        """failed and error are both terminal, neither success-like, but distinct.

        This test documents the semantic boundary: failed = domain-level
        negative outcome, error = infrastructure/tooling failure.
        """
        failed = EnumSkillResultStatus.FAILED
        error = EnumSkillResultStatus.ERROR
        # Both terminal
        assert failed.is_terminal
        assert error.is_terminal
        # Neither success-like
        assert not failed.is_success_like
        assert not error.is_success_like
        # But they are distinct values
        assert failed is not error
        assert failed.value != error.value

    def test_partial_is_both_terminal_and_success_like(self) -> None:
        """partial is a terminal positive outcome (degraded but usable)."""
        partial = EnumSkillResultStatus.PARTIAL
        assert partial.is_terminal
        assert partial.is_success_like

    def test_membership_via_string(self) -> None:
        """Enum members compare equal to their string values (str inheritance)."""
        assert EnumSkillResultStatus.SUCCESS == "success"
        assert EnumSkillResultStatus.GATED == "gated"
