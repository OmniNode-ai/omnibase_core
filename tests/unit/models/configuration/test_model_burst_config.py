"""Tests for ModelBurstConfig."""

import pytest

from omnibase_core.models.configuration.model_burst_config import ModelBurstConfig


class TestModelBurstConfigBasics:
    def test_create_default(self):
        config = ModelBurstConfig()
        assert config.burst_detection_enabled is True
        assert config.burst_capacity_multiplier == 2.0

    def test_create_with_custom_values(self):
        config = ModelBurstConfig(
            burst_capacity_multiplier=3.0, burst_duration_seconds=60
        )
        assert config.burst_capacity_multiplier == 3.0
        assert config.burst_duration_seconds == 60


class TestModelBurstConfigMethods:
    def test_get_burst_capacity(self):
        config = ModelBurstConfig(burst_capacity_multiplier=2.0)
        capacity = config.get_burst_capacity(100)
        assert capacity == 200

    def test_get_burst_capacity_with_max(self):
        config = ModelBurstConfig(
            burst_capacity_multiplier=10.0, max_burst_capacity=500
        )
        capacity = config.get_burst_capacity(100)
        assert capacity == 500

    def test_get_burst_threshold(self):
        config = ModelBurstConfig(burst_threshold_multiplier=1.5)
        threshold = config.get_burst_threshold(100)
        assert threshold == 150

    def test_is_burst_triggered_enabled(self):
        config = ModelBurstConfig(
            burst_detection_enabled=True, burst_threshold_multiplier=1.5
        )
        assert config.is_burst_triggered(200.0, 100) is True
        assert config.is_burst_triggered(100.0, 100) is False

    def test_is_burst_triggered_disabled(self):
        config = ModelBurstConfig(burst_detection_enabled=False)
        assert config.is_burst_triggered(1000.0, 100) is False

    def test_calculate_degraded_capacity(self):
        config = ModelBurstConfig(burst_degradation_rate=0.1)
        degraded = config.calculate_degraded_capacity(100, 5.0)
        assert degraded == 50

    def test_should_warn_about_burst(self):
        config = ModelBurstConfig(burst_warning_threshold=0.8)
        assert config.should_warn_about_burst(85, 100) is True
        assert config.should_warn_about_burst(70, 100) is False

    def test_can_allow_overflow(self):
        config = ModelBurstConfig(allow_burst_overflow=True)
        assert config.can_allow_overflow(150, 100) is True

    def test_calculate_overflow_penalty(self):
        config = ModelBurstConfig(overflow_penalty_multiplier=3.0)
        penalty = config.calculate_overflow_penalty(50)
        assert penalty == 3.0

    def test_is_in_cooldown(self):
        config = ModelBurstConfig(burst_cooldown_seconds=60)
        assert config.is_in_cooldown(100.0, 150.0) is True
        assert config.is_in_cooldown(100.0, 200.0) is False

    def test_is_in_grace_period(self):
        config = ModelBurstConfig(burst_grace_period_seconds=5)
        assert config.is_in_grace_period(100.0, 103.0) is True
        assert config.is_in_grace_period(100.0, 110.0) is False

    def test_get_adaptive_burst_size(self):
        config = ModelBurstConfig(adaptive_burst_sizing=True)
        peaks = [100, 150, 200, 250, 300]
        adaptive = config.get_adaptive_burst_size(peaks, 100)
        assert adaptive >= 200

    def test_get_adaptive_burst_size_disabled(self):
        config = ModelBurstConfig(adaptive_burst_sizing=False)
        peaks = [100, 150, 200]
        adaptive = config.get_adaptive_burst_size(peaks, 100)
        assert adaptive == 200


class TestModelBurstConfigSerialization:
    def test_serialization(self):
        config = ModelBurstConfig(burst_capacity_multiplier=3.0)
        data = config.model_dump()
        assert data["burst_capacity_multiplier"] == 3.0

    def test_roundtrip(self):
        original = ModelBurstConfig(burst_capacity_multiplier=3.0)
        data = original.model_dump()
        restored = ModelBurstConfig.model_validate(data)
        assert restored.burst_capacity_multiplier == original.burst_capacity_multiplier
