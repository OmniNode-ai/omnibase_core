"""
Tests for ModelComputeCacheConfig.

Comprehensive tests for compute cache configuration model.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.configuration.model_compute_cache_config import (
    ModelComputeCacheConfig,
)


class TestModelComputeCacheConfigInitialization:
    """Test ModelComputeCacheConfig initialization."""

    def test_create_default_config(self):
        """Test creating config with default values."""
        config = ModelComputeCacheConfig()
        assert config is not None
        assert isinstance(config, ModelComputeCacheConfig)
        assert config.max_size == 128
        assert config.ttl_seconds == 3600
        assert config.eviction_policy == "lru"
        assert config.enable_stats is True

    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = ModelComputeCacheConfig(
            max_size=512,
            ttl_seconds=7200,
            eviction_policy="lfu",
            enable_stats=False,
        )
        assert config.max_size == 512
        assert config.ttl_seconds == 7200
        assert config.eviction_policy == "lfu"
        assert config.enable_stats is False

    def test_config_inheritance(self):
        """Test that ModelComputeCacheConfig inherits from BaseModel."""
        from pydantic import BaseModel

        config = ModelComputeCacheConfig()
        assert isinstance(config, BaseModel)


class TestModelComputeCacheConfigValidation:
    """Test ModelComputeCacheConfig field validation."""

    def test_max_size_validation_bounds(self):
        """Test max_size field constraints."""
        # Valid values
        config = ModelComputeCacheConfig(max_size=1)
        assert config.max_size == 1

        config = ModelComputeCacheConfig(max_size=10000)
        assert config.max_size == 10000

        # Default value
        config = ModelComputeCacheConfig()
        assert config.max_size == 128

    def test_max_size_validation_errors(self):
        """Test max_size validation errors."""
        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ModelComputeCacheConfig(max_size=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelComputeCacheConfig(max_size=10001)
        assert "less than or equal to 10000" in str(exc_info.value)

    def test_ttl_seconds_validation(self):
        """Test ttl_seconds field validation."""
        # Valid values
        config = ModelComputeCacheConfig(ttl_seconds=1)
        assert config.ttl_seconds == 1

        config = ModelComputeCacheConfig(ttl_seconds=86400)  # 24 hours
        assert config.ttl_seconds == 86400

        # None value (no expiration)
        config = ModelComputeCacheConfig(ttl_seconds=None)
        assert config.ttl_seconds is None

    def test_ttl_seconds_validation_errors(self):
        """Test ttl_seconds validation errors."""
        # Below minimum (when not None)
        with pytest.raises(ValidationError) as exc_info:
            ModelComputeCacheConfig(ttl_seconds=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_eviction_policy_validation(self):
        """Test eviction_policy field validation."""
        # Valid policies
        for policy in ["lru", "lfu", "fifo"]:
            config = ModelComputeCacheConfig(eviction_policy=policy)
            assert config.eviction_policy == policy

    def test_eviction_policy_validation_errors(self):
        """Test eviction_policy validation errors."""
        # Invalid policy
        with pytest.raises(ValidationError) as exc_info:
            ModelComputeCacheConfig(eviction_policy="invalid")
        # Pydantic v2 uses "enum" in error message, not "pattern"
        assert "enum" in str(exc_info.value).lower()

    def test_enable_stats_validation(self):
        """Test enable_stats field validation."""
        config = ModelComputeCacheConfig(enable_stats=True)
        assert config.enable_stats is True

        config = ModelComputeCacheConfig(enable_stats=False)
        assert config.enable_stats is False


class TestModelComputeCacheConfigSerialization:
    """Test ModelComputeCacheConfig serialization."""

    def test_config_serialization(self):
        """Test config model_dump."""
        config = ModelComputeCacheConfig(
            max_size=512,
            ttl_seconds=7200,
            eviction_policy="lfu",
            enable_stats=False,
        )
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["max_size"] == 512
        assert data["ttl_seconds"] == 7200
        assert data["eviction_policy"] == "lfu"
        assert data["enable_stats"] is False

    def test_config_deserialization(self):
        """Test config model_validate."""
        data = {
            "max_size": 1024,
            "ttl_seconds": 3600,
            "eviction_policy": "lru",
            "enable_stats": True,
        }
        config = ModelComputeCacheConfig.model_validate(data)
        assert config.max_size == 1024
        assert config.ttl_seconds == 3600
        assert config.eviction_policy == "lru"
        assert config.enable_stats is True

    def test_config_json_serialization(self):
        """Test config JSON serialization."""
        config = ModelComputeCacheConfig()
        json_data = config.model_dump_json()
        assert isinstance(json_data, str)
        assert "max_size" in json_data
        assert "ttl_seconds" in json_data
        assert "eviction_policy" in json_data

    def test_config_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelComputeCacheConfig(
            max_size=2048,
            ttl_seconds=1800,
            eviction_policy="fifo",
            enable_stats=True,
        )
        data = original.model_dump()
        restored = ModelComputeCacheConfig.model_validate(data)
        assert restored.max_size == original.max_size
        assert restored.ttl_seconds == original.ttl_seconds
        assert restored.eviction_policy == original.eviction_policy
        assert restored.enable_stats == original.enable_stats


class TestModelComputeCacheConfigMethods:
    """Test ModelComputeCacheConfig methods."""

    def test_get_ttl_minutes_conversion(self):
        """Test get_ttl_minutes converts seconds to minutes."""
        config = ModelComputeCacheConfig(ttl_seconds=3600)  # 1 hour
        assert config.get_ttl_minutes() == 60

        config = ModelComputeCacheConfig(ttl_seconds=1800)  # 30 minutes
        assert config.get_ttl_minutes() == 30

    def test_get_ttl_minutes_with_none(self):
        """Test get_ttl_minutes returns None when ttl_seconds is None."""
        config = ModelComputeCacheConfig(ttl_seconds=None)
        assert config.get_ttl_minutes() is None

    def test_get_ttl_minutes_with_partial_minutes(self):
        """Test get_ttl_minutes with partial minutes (integer division)."""
        config = ModelComputeCacheConfig(ttl_seconds=90)  # 1.5 minutes
        assert config.get_ttl_minutes() == 1  # Integer division

    def test_get_effective_ttl_seconds(self):
        """Test get_effective_ttl_seconds."""
        config = ModelComputeCacheConfig(ttl_seconds=3600)
        assert config.get_effective_ttl_seconds() == 3600

    def test_get_effective_ttl_seconds_with_none(self):
        """Test get_effective_ttl_seconds returns 0 when None."""
        config = ModelComputeCacheConfig(ttl_seconds=None)
        assert config.get_effective_ttl_seconds() == 0

    def test_validate_memory_requirements_default(self):
        """Test validate_memory_requirements with default entry size."""
        config = ModelComputeCacheConfig(max_size=128)
        memory = config.validate_memory_requirements()

        assert isinstance(memory, dict)
        assert "estimated_memory_mb" in memory
        assert "max_memory_mb" in memory
        assert "entries_per_mb" in memory

        # 128 entries × 1KB / 1024 = 0.125 MB
        assert memory["estimated_memory_mb"] == 0.12
        assert memory["max_memory_mb"] == 0.15  # 20% overhead (rounded)
        assert memory["entries_per_mb"] == 1024.0

    def test_validate_memory_requirements_custom_entry_size(self):
        """Test validate_memory_requirements with custom entry size."""
        config = ModelComputeCacheConfig(max_size=1024)
        memory = config.validate_memory_requirements(avg_entry_size_kb=10.0)

        # 1024 entries × 10KB / 1024 = 10 MB
        assert memory["estimated_memory_mb"] == 10.0
        assert memory["max_memory_mb"] == 12.0  # 20% overhead
        assert memory["entries_per_mb"] == 102.4

    def test_validate_memory_requirements_large_cache(self):
        """Test validate_memory_requirements for large cache."""
        config = ModelComputeCacheConfig(max_size=10000)
        memory = config.validate_memory_requirements()

        # 10000 entries × 1KB / 1024 = 9.77 MB
        assert memory["estimated_memory_mb"] == 9.77
        assert memory["max_memory_mb"] == 11.72  # 20% overhead


class TestModelComputeCacheConfigEdgeCases:
    """Test cache config edge cases."""

    def test_minimum_max_size(self):
        """Test minimum max_size value."""
        config = ModelComputeCacheConfig(max_size=1)
        assert config.max_size == 1

    def test_maximum_max_size(self):
        """Test maximum max_size value."""
        config = ModelComputeCacheConfig(max_size=10000)
        assert config.max_size == 10000

    def test_minimum_ttl_seconds(self):
        """Test minimum ttl_seconds value."""
        config = ModelComputeCacheConfig(ttl_seconds=1)
        assert config.ttl_seconds == 1

    def test_stats_enabled_by_default(self):
        """Test statistics are enabled by default."""
        config = ModelComputeCacheConfig()
        assert config.enable_stats is True

    def test_lru_policy_by_default(self):
        """Test LRU is default eviction policy."""
        config = ModelComputeCacheConfig()
        assert config.eviction_policy == "lru"

    def test_ttl_none_for_no_expiration(self):
        """Test ttl_seconds=None for no expiration."""
        config = ModelComputeCacheConfig(ttl_seconds=None)
        assert config.ttl_seconds is None
        assert config.get_ttl_minutes() is None
        assert config.get_effective_ttl_seconds() == 0


class TestModelComputeCacheConfigAttributes:
    """Test cache config attributes and metadata."""

    def test_config_attributes(self):
        """Test that config has expected attributes."""
        config = ModelComputeCacheConfig()
        assert hasattr(config, "model_dump")
        assert callable(config.model_dump)
        assert hasattr(ModelComputeCacheConfig, "model_validate")
        assert callable(ModelComputeCacheConfig.model_validate)

    def test_config_docstring(self):
        """Test config docstring."""
        assert ModelComputeCacheConfig.__doc__ is not None
        assert "cache" in ModelComputeCacheConfig.__doc__.lower()

    def test_config_class_name(self):
        """Test config class name."""
        assert ModelComputeCacheConfig.__name__ == "ModelComputeCacheConfig"

    def test_config_module(self):
        """Test config module."""
        assert (
            ModelComputeCacheConfig.__module__
            == "omnibase_core.models.configuration.model_compute_cache_config"
        )

    def test_config_copy(self):
        """Test config copying."""
        config = ModelComputeCacheConfig(max_size=256)
        copied = config.model_copy()
        assert copied is not None
        assert copied.max_size == 256
        assert copied is not config

    def test_config_equality(self):
        """Test config equality."""
        config1 = ModelComputeCacheConfig(max_size=128)
        config2 = ModelComputeCacheConfig(max_size=128)
        assert config1 == config2

    def test_config_str_repr(self):
        """Test config string representations."""
        config = ModelComputeCacheConfig()
        str_repr = str(config)
        assert isinstance(str_repr, str)

        repr_str = repr(config)
        assert isinstance(repr_str, str)
        assert "ModelComputeCacheConfig" in repr_str


class TestModelComputeCacheConfigProductionScenarios:
    """Test production deployment scenarios."""

    def test_small_workload_config(self):
        """Test configuration for small workloads."""
        config = ModelComputeCacheConfig(
            max_size=128, ttl_seconds=1800, eviction_policy="lru"
        )
        memory = config.validate_memory_requirements()
        assert memory["estimated_memory_mb"] < 1.0  # Less than 1MB

    def test_medium_workload_config(self):
        """Test configuration for medium workloads."""
        config = ModelComputeCacheConfig(
            max_size=512, ttl_seconds=3600, eviction_policy="lru"
        )
        memory = config.validate_memory_requirements()
        assert 0.4 <= memory["estimated_memory_mb"] <= 0.6  # ~0.5MB

    def test_large_workload_config(self):
        """Test configuration for large workloads."""
        config = ModelComputeCacheConfig(
            max_size=2048, ttl_seconds=7200, eviction_policy="lfu"
        )
        memory = config.validate_memory_requirements()
        assert 1.5 <= memory["estimated_memory_mb"] <= 2.5  # ~2MB

    def test_no_expiration_config(self):
        """Test configuration with no expiration for immutable data."""
        config = ModelComputeCacheConfig(max_size=1024, ttl_seconds=None)
        assert config.ttl_seconds is None
        assert config.get_effective_ttl_seconds() == 0

    def test_stats_disabled_for_low_latency(self):
        """Test configuration with stats disabled for ultra-low latency."""
        config = ModelComputeCacheConfig(enable_stats=False)
        assert config.enable_stats is False
