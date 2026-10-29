# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shrink-only baseline comparison (OMN-21503)."""

import pytest

from omnibase_core.handlers.handler_shrink_only_baseline import (
    compare_shrink_only,
    verdict_issues,
)


@pytest.mark.unit
class TestCompareShrinkOnly:
    def test_equal_sets_are_ok(self) -> None:
        verdict = compare_shrink_only("k", ["a", "b"], ["a", "b"])
        assert verdict.ok
        assert verdict_issues(verdict) == ()

    def test_new_fingerprint_fails(self) -> None:
        verdict = compare_shrink_only("k", ["a", "b", "c"], ["a", "b"])
        assert not verdict.ok
        assert verdict.added == ("c",)
        assert [i.code for i in verdict_issues(verdict)] == ["baseline_added"]

    def test_repeated_fingerprint_is_a_multiset(self) -> None:
        verdict = compare_shrink_only("k", ["a", "a"], ["a"])
        assert verdict.added == ("a",)

    def test_shrinking_is_ok_and_reports_stale(self) -> None:
        verdict = compare_shrink_only("k", ["a"], ["a", "b"])
        assert verdict.ok
        assert verdict.stale == ("b",)

    def test_raised_baseline_fails_even_when_current_matches(self) -> None:
        verdict = compare_shrink_only("k", ["a", "b"], ["a", "b"], ["a"])
        assert not verdict.ok
        assert verdict.raised == ("b",)
        assert [i.code for i in verdict_issues(verdict)] == ["baseline_raised"]

    def test_shrunk_baseline_against_previous_is_ok(self) -> None:
        verdict = compare_shrink_only("k", ["a"], ["a"], ["a", "b"])
        assert verdict.ok
        assert verdict.previous_count == 2
