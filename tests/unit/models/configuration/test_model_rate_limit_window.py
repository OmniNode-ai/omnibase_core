"""Tests for ModelRateLimitWindow."""

import pytest

from omnibase_core.models.configuration.model_rate_limit_window import (
    ModelRateLimitWindow,
)


@pytest.mark.unit
class TestModelRateLimitWindowBasics:
    def test_create_default(self):
        window = ModelRateLimitWindow()
        assert window.window_type == "sliding"
        assert window.window_duration_seconds == 60
        assert window.window_size == 100

    def test_window_type_validation(self):
        for wtype in ["fixed", "sliding", "token_bucket", "leaky_bucket"]:
            window = ModelRateLimitWindow(window_type=wtype)
            assert window.window_type == wtype


@pytest.mark.unit
class TestModelRateLimitWindowMethods:
    def test_get_effective_window_size_no_burst(self):
        window = ModelRateLimitWindow(window_size=100, allow_burst_above_limit=False)
        assert window.get_effective_window_size() == 100

    def test_get_effective_window_size_with_burst(self):
        window = ModelRateLimitWindow(
            window_size=100, allow_burst_above_limit=True, burst_multiplier=2.0
        )
        assert window.get_effective_window_size() == 200

    def test_get_sub_window_duration(self):
        window = ModelRateLimitWindow(window_duration_seconds=60, sub_window_count=12)
        assert window.get_sub_window_duration() == 5.0

    def test_get_requests_per_second_limit(self):
        window = ModelRateLimitWindow(window_size=100, window_duration_seconds=60)
        assert abs(window.get_requests_per_second_limit() - 1.666) < 0.01

    def test_calculate_window_start_fixed(self):
        window = ModelRateLimitWindow(window_type="fixed", window_duration_seconds=60)
        start = window.calculate_window_start(125.0)
        assert start == 120.0

    def test_calculate_window_start_sliding(self):
        window = ModelRateLimitWindow(window_type="sliding", window_duration_seconds=60)
        start = window.calculate_window_start(125.0)
        assert start == 65.0

    def test_is_within_current_window(self):
        window = ModelRateLimitWindow()
        assert window.is_within_current_window(50.0, 0.0) is True
        assert window.is_within_current_window(70.0, 0.0) is False

    def test_get_tokens_to_add(self):
        window = ModelRateLimitWindow(
            window_type="token_bucket", token_refill_rate=10.0
        )
        tokens = window.get_tokens_to_add(5.0)
        assert tokens == 50.0

    def test_get_requests_to_leak(self):
        window = ModelRateLimitWindow(window_type="leaky_bucket", leak_rate=5.0)
        leaked = window.get_requests_to_leak(10.0)
        assert leaked == 50.0


@pytest.mark.unit
class TestModelRateLimitWindowFactoryMethods:
    def test_create_fixed_window(self):
        window = ModelRateLimitWindow.create_fixed_window(120, 200)
        assert window.window_type == "fixed"
        assert window.window_duration_seconds == 120
        assert window.window_size == 200

    def test_create_sliding_window(self):
        window = ModelRateLimitWindow.create_sliding_window(60, 100, 12)
        assert window.window_type == "sliding"
        assert window.sub_window_count == 12

    def test_create_token_bucket(self):
        window = ModelRateLimitWindow.create_token_bucket(100, 10.0)
        assert window.window_type == "token_bucket"
        assert window.token_refill_rate == 10.0

    def test_create_leaky_bucket(self):
        window = ModelRateLimitWindow.create_leaky_bucket(100, 5.0)
        assert window.window_type == "leaky_bucket"
        assert window.leak_rate == 5.0

    def test_create_burst_friendly(self):
        window = ModelRateLimitWindow.create_burst_friendly(100, 2.0)
        assert window.allow_burst_above_limit is True
        assert window.burst_multiplier == 2.0


@pytest.mark.unit
class TestModelRateLimitWindowSerialization:
    def test_serialization(self):
        window = ModelRateLimitWindow(window_size=200)
        data = window.model_dump()
        assert data["window_size"] == 200

    def test_roundtrip(self):
        original = ModelRateLimitWindow(window_size=200)
        data = original.model_dump()
        restored = ModelRateLimitWindow.model_validate(data)
        assert restored.window_size == original.window_size
