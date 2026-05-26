# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ServiceTimeInjector and UtilStreamingWindow replay determinism.

Proves that timestamps are injectable — the acceptance criterion for OMN-12163.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector
from omnibase_core.utils.util_streaming_window import UtilStreamingWindow


class TestServiceTimeInjector:
    """ServiceTimeInjector: production mode and replay mode behaviour."""

    @pytest.mark.unit
    def test_production_mode_returns_utc_datetime(self) -> None:
        svc = ServiceTimeInjector()
        result = svc.now()
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    @pytest.mark.unit
    def test_replay_mode_returns_fixed_time(self) -> None:
        fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        assert svc.now() == fixed

    @pytest.mark.unit
    def test_replay_mode_is_deterministic(self) -> None:
        fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        t1 = svc.now()
        t2 = svc.now()
        assert t1 == t2 == fixed

    @pytest.mark.unit
    def test_two_injectors_same_fixed_time_are_equal(self) -> None:
        fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        a = ServiceTimeInjector(fixed_time=fixed)
        b = ServiceTimeInjector(fixed_time=fixed)
        assert a.now() == b.now() == fixed

    @pytest.mark.unit
    def test_naive_fixed_time_assumes_utc(self) -> None:
        naive = datetime(2024, 6, 15, 12, 0, 0)
        svc = ServiceTimeInjector(fixed_time=naive)
        result = svc.now()
        assert result.tzinfo == UTC

    @pytest.mark.unit
    def test_utc_now_alias_matches_now(self) -> None:
        fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        assert svc.utc_now() == svc.now()

    @pytest.mark.unit
    def test_fixed_time_property(self) -> None:
        fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        assert svc.fixed_time == fixed

    @pytest.mark.unit
    def test_production_mode_fixed_time_is_none(self) -> None:
        svc = ServiceTimeInjector()
        assert svc.fixed_time is None


class TestUtilStreamingWindowWithInjectedTime:
    """UtilStreamingWindow: injectable time for deterministic replay."""

    @pytest.mark.unit
    def test_window_start_uses_injected_time(self) -> None:
        fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        window = UtilStreamingWindow(window_size_ms=1000, time_svc=svc)
        assert window.window_start == fixed

    @pytest.mark.unit
    def test_add_item_uses_injected_time_for_timestamps(self) -> None:
        fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        window = UtilStreamingWindow(window_size_ms=1000, time_svc=svc)
        window.add_item("event_a")
        _item, ts = next(iter(window.buffer))
        assert ts == fixed

    @pytest.mark.unit
    def test_window_never_completes_when_time_is_frozen(self) -> None:
        fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        window = UtilStreamingWindow(window_size_ms=5000, time_svc=svc)
        for _ in range(10):
            ready = window.add_item("event")
            assert not ready

    @pytest.mark.unit
    def test_window_immediately_complete_when_size_is_zero(self) -> None:
        fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        window = UtilStreamingWindow(window_size_ms=0, time_svc=svc)
        ready = window.add_item("event")
        assert ready

    @pytest.mark.unit
    def test_advance_window_uses_injected_time(self) -> None:
        fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        svc = ServiceTimeInjector(fixed_time=fixed)
        window = UtilStreamingWindow(window_size_ms=1000, time_svc=svc)
        window.add_item("event")
        window.advance_window()
        assert window.window_start == fixed
        assert len(window.buffer) == 0

    @pytest.mark.unit
    def test_default_construction_uses_real_time(self) -> None:
        window = UtilStreamingWindow(window_size_ms=1000)
        before = datetime.now(UTC)
        ready = window.add_item("event")
        after = datetime.now(UTC)
        _item, ts = next(iter(window.buffer))
        assert before <= ts <= after
        assert not ready
