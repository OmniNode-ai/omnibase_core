# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from omnibase_core.agents.prm_detectors import (
    detect_context_thrash,
    detect_expansion_drift,
    detect_ping_pong,
    detect_repetition_loop,
    detect_stuck_on_test,
)
from omnibase_core.enums.enum_prm_pattern import EnumPrmPattern
from omnibase_core.models.agents.model_trajectory_entry import ModelTrajectoryEntry


def _entry(
    step: int, agent: str, action: str, target: str, result: str = "ok"
) -> ModelTrajectoryEntry:
    return ModelTrajectoryEntry(
        step=step, agent=agent, action=action, target=target, result=result
    )


# ── detect_repetition_loop ────────────────────────────────────────────────────


class TestDetectRepetitionLoop:
    def test_empty_entries_returns_empty(self) -> None:
        assert detect_repetition_loop([], last_processed_step=0) == []

    def test_no_repeat_returns_empty(self) -> None:
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "edit", "bar.py"),
            _entry(3, "A", "test", "foo.py"),
        ]
        assert detect_repetition_loop(entries, last_processed_step=0) == []

    def test_detects_repeated_triple_in_window(self) -> None:
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "test", "bar.py"),
            _entry(3, "A", "edit", "foo.py"),  # repeat of step 1
            _entry(4, "A", "review", "baz.py"),
            _entry(5, "A", "edit", "foo.py"),  # third occurrence but same window
        ]
        matches = detect_repetition_loop(entries, last_processed_step=0)
        assert len(matches) >= 1
        assert all(m.pattern == EnumPrmPattern.REPETITION_LOOP for m in matches)

    def test_skips_match_already_processed(self) -> None:
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "test", "bar.py"),
            _entry(3, "A", "edit", "foo.py"),
        ]
        matches = detect_repetition_loop(entries, last_processed_step=5)
        assert matches == []

    def test_dedup_key_format(self) -> None:
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "B", "other", "baz.py"),
            _entry(3, "A", "edit", "foo.py"),
            _entry(4, "C", "other", "qux.py"),
            _entry(5, "A", "edit", "foo.py"),
        ]
        matches = detect_repetition_loop(entries, last_processed_step=0)
        assert len(matches) >= 1
        # dedup_key format: pattern:agents:targets:start-end
        key = matches[0].dedup_key
        assert key.startswith("repetition_loop:")
        parts = key.split(":")
        assert len(parts) == 4  # pattern:agents:targets:range

    def test_window_boundary_no_false_positive(self) -> None:
        # 12 unique triples, window=10 so no window contains a repeat
        entries = [_entry(i, f"A{i}", "edit", f"file{i}.py") for i in range(1, 13)]
        assert detect_repetition_loop(entries, last_processed_step=0) == []


# ── detect_ping_pong ──────────────────────────────────────────────────────────


class TestDetectPingPong:
    def test_empty_returns_empty(self) -> None:
        assert detect_ping_pong([], last_processed_step=0) == []

    def test_no_delegate_returns_empty(self) -> None:
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "B", "review", "foo.py"),
            _entry(3, "A", "edit", "foo.py"),
        ]
        assert detect_ping_pong(entries, last_processed_step=0) == []

    def test_detects_aba_pattern(self) -> None:
        # A→B→A with same target appearing ≥3 times in window 5
        entries = [
            _entry(1, "A", "delegate", "task.py"),
            _entry(2, "B", "delegate", "task.py"),
            _entry(3, "A", "delegate", "task.py"),
            _entry(4, "B", "delegate", "task.py"),
            _entry(5, "A", "delegate", "task.py"),
        ]
        matches = detect_ping_pong(entries, last_processed_step=0)
        assert len(matches) >= 1
        assert all(m.pattern == EnumPrmPattern.PING_PONG for m in matches)

    def test_no_aba_pattern_no_match(self) -> None:
        # A→B→C pattern, no ping-pong
        entries = [
            _entry(1, "A", "delegate", "task.py"),
            _entry(2, "B", "delegate", "task.py"),
            _entry(3, "C", "delegate", "task.py"),
        ]
        assert detect_ping_pong(entries, last_processed_step=0) == []

    def test_skips_already_processed(self) -> None:
        entries = [
            _entry(1, "A", "delegate", "task.py"),
            _entry(2, "B", "delegate", "task.py"),
            _entry(3, "A", "delegate", "task.py"),
            _entry(4, "B", "delegate", "task.py"),
            _entry(5, "A", "delegate", "task.py"),
        ]
        matches = detect_ping_pong(entries, last_processed_step=10)
        assert matches == []

    def test_dedup_key_format(self) -> None:
        entries = [
            _entry(1, "A", "delegate", "task.py"),
            _entry(2, "B", "delegate", "task.py"),
            _entry(3, "A", "delegate", "task.py"),
            _entry(4, "B", "delegate", "task.py"),
            _entry(5, "A", "delegate", "task.py"),
        ]
        matches = detect_ping_pong(entries, last_processed_step=0)
        assert len(matches) >= 1
        key = matches[0].dedup_key
        assert key.startswith("ping_pong:")


# ── detect_expansion_drift ────────────────────────────────────────────────────


class TestDetectExpansionDrift:
    def test_empty_returns_empty(self) -> None:
        assert detect_expansion_drift([], last_processed_step=0) == []

    def test_fewer_than_two_windows_returns_empty(self) -> None:
        # Only 15 entries — not enough for two windows of N=20
        entries = [_entry(i, "A", "edit", f"file{i}.py") for i in range(1, 16)]
        assert detect_expansion_drift(entries, last_processed_step=0) == []

    def test_detects_expansion_drift(self) -> None:
        # Prev window: 4 unique targets; recent window: 7 unique targets → ratio 1.75 > 1.5
        prev_entries = [_entry(i, "A", "edit", f"file{i % 4}.py") for i in range(1, 21)]
        recent_entries = [
            _entry(i + 20, "A", "edit", f"new_file{i}.py") for i in range(1, 21)
        ]
        entries = prev_entries + recent_entries
        matches = detect_expansion_drift(entries, last_processed_step=0)
        assert len(matches) >= 1
        assert all(m.pattern == EnumPrmPattern.EXPANSION_DRIFT for m in matches)

    def test_no_drift_stable_unique_count(self) -> None:
        # Same 4 targets in both windows → ratio = 1.0, no drift
        entries = [_entry(i, "A", "edit", f"file{i % 4}.py") for i in range(1, 41)]
        assert detect_expansion_drift(entries, last_processed_step=0) == []

    def test_skips_already_processed(self) -> None:
        prev_entries = [_entry(i, "A", "edit", f"file{i % 4}.py") for i in range(1, 21)]
        recent_entries = [
            _entry(i + 20, "A", "edit", f"new_file{i}.py") for i in range(1, 21)
        ]
        entries = prev_entries + recent_entries
        matches = detect_expansion_drift(entries, last_processed_step=100)
        assert matches == []

    def test_dedup_key_format(self) -> None:
        prev_entries = [_entry(i, "A", "edit", f"file{i % 4}.py") for i in range(1, 21)]
        recent_entries = [
            _entry(i + 20, "A", "edit", f"new_file{i}.py") for i in range(1, 21)
        ]
        entries = prev_entries + recent_entries
        matches = detect_expansion_drift(entries, last_processed_step=0)
        if matches:
            key = matches[0].dedup_key
            assert key.startswith("expansion_drift:")


# ── detect_stuck_on_test ──────────────────────────────────────────────────────


class TestDetectStuckOnTest:
    def test_empty_returns_empty(self) -> None:
        assert detect_stuck_on_test([], last_processed_step=0) == []

    def test_fewer_than_threshold_cycles_returns_empty(self) -> None:
        # Only 2 edit→test_fail→edit cycles for foo.py, threshold is 3
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "test_fail", "foo.py"),
            _entry(3, "A", "edit", "foo.py"),
            _entry(4, "A", "test_fail", "foo.py"),
            _entry(5, "A", "edit", "foo.py"),
        ]
        assert detect_stuck_on_test(entries, last_processed_step=0) == []

    def test_detects_stuck_on_test(self) -> None:
        # 3 edit→test_fail→edit cycles for foo.py
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "test_fail", "foo.py"),
            _entry(3, "A", "edit", "foo.py"),
            _entry(4, "A", "test_fail", "foo.py"),
            _entry(5, "A", "edit", "foo.py"),
            _entry(6, "A", "test_fail", "foo.py"),
            _entry(7, "A", "edit", "foo.py"),
        ]
        matches = detect_stuck_on_test(entries, last_processed_step=0)
        assert len(matches) >= 1
        assert all(m.pattern == EnumPrmPattern.STUCK_ON_TEST for m in matches)

    def test_no_false_positive_different_targets(self) -> None:
        # Cycles spread across different targets — no single target hits threshold
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "test_fail", "foo.py"),
            _entry(3, "A", "edit", "bar.py"),
            _entry(4, "A", "test_fail", "bar.py"),
            _entry(5, "A", "edit", "baz.py"),
            _entry(6, "A", "test_fail", "baz.py"),
        ]
        assert detect_stuck_on_test(entries, last_processed_step=0) == []

    def test_skips_already_processed(self) -> None:
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "test_fail", "foo.py"),
            _entry(3, "A", "edit", "foo.py"),
            _entry(4, "A", "test_fail", "foo.py"),
            _entry(5, "A", "edit", "foo.py"),
            _entry(6, "A", "test_fail", "foo.py"),
            _entry(7, "A", "edit", "foo.py"),
        ]
        matches = detect_stuck_on_test(entries, last_processed_step=10)
        assert matches == []

    def test_dedup_key_format(self) -> None:
        entries = [
            _entry(1, "A", "edit", "foo.py"),
            _entry(2, "A", "test_fail", "foo.py"),
            _entry(3, "A", "edit", "foo.py"),
            _entry(4, "A", "test_fail", "foo.py"),
            _entry(5, "A", "edit", "foo.py"),
            _entry(6, "A", "test_fail", "foo.py"),
            _entry(7, "A", "edit", "foo.py"),
        ]
        matches = detect_stuck_on_test(entries, last_processed_step=0)
        assert len(matches) >= 1
        key = matches[0].dedup_key
        assert key.startswith("stuck_on_test:")


# ── detect_context_thrash ─────────────────────────────────────────────────────


class TestDetectContextThrash:
    def test_empty_returns_empty(self) -> None:
        assert detect_context_thrash([], last_processed_step=0) == []

    def test_fewer_than_five_consecutive_new_targets_returns_empty(self) -> None:
        # 4 new targets then a revisit
        entries = [
            _entry(1, "A", "edit", "a.py"),
            _entry(2, "A", "edit", "b.py"),
            _entry(3, "A", "edit", "c.py"),
            _entry(4, "A", "edit", "d.py"),
            _entry(5, "A", "edit", "a.py"),  # revisit breaks streak
        ]
        assert detect_context_thrash(entries, last_processed_step=0) == []

    def test_detects_context_thrash(self) -> None:
        # 6 consecutive new targets with no revisits
        entries = [
            _entry(1, "A", "edit", "a.py"),
            _entry(2, "A", "edit", "b.py"),
            _entry(3, "A", "edit", "c.py"),
            _entry(4, "A", "edit", "d.py"),
            _entry(5, "A", "edit", "e.py"),
            _entry(6, "A", "edit", "f.py"),
        ]
        matches = detect_context_thrash(entries, last_processed_step=0)
        assert len(matches) >= 1
        assert all(m.pattern == EnumPrmPattern.CONTEXT_THRASH for m in matches)

    def test_revisit_resets_streak(self) -> None:
        # 4 new targets, then revisit, then 5 more new targets
        entries = [
            _entry(1, "A", "edit", "a.py"),
            _entry(2, "A", "edit", "b.py"),
            _entry(3, "A", "edit", "c.py"),
            _entry(4, "A", "edit", "d.py"),
            _entry(5, "A", "edit", "a.py"),  # revisit resets
            _entry(6, "A", "edit", "e.py"),
            _entry(7, "A", "edit", "f.py"),
            _entry(8, "A", "edit", "g.py"),
            _entry(9, "A", "edit", "h.py"),
            _entry(10, "A", "edit", "i.py"),
        ]
        # After revisit at step 5, steps 6-10 are 5 new consecutive targets
        matches = detect_context_thrash(entries, last_processed_step=0)
        assert len(matches) >= 1

    def test_skips_already_processed(self) -> None:
        entries = [
            _entry(1, "A", "edit", "a.py"),
            _entry(2, "A", "edit", "b.py"),
            _entry(3, "A", "edit", "c.py"),
            _entry(4, "A", "edit", "d.py"),
            _entry(5, "A", "edit", "e.py"),
            _entry(6, "A", "edit", "f.py"),
        ]
        matches = detect_context_thrash(entries, last_processed_step=10)
        assert matches == []

    def test_dedup_key_format(self) -> None:
        entries = [
            _entry(1, "A", "edit", "a.py"),
            _entry(2, "A", "edit", "b.py"),
            _entry(3, "A", "edit", "c.py"),
            _entry(4, "A", "edit", "d.py"),
            _entry(5, "A", "edit", "e.py"),
            _entry(6, "A", "edit", "f.py"),
        ]
        matches = detect_context_thrash(entries, last_processed_step=0)
        assert len(matches) >= 1
        key = matches[0].dedup_key
        assert key.startswith("context_thrash:")
