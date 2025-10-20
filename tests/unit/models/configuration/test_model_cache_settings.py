"""
Tests for ModelCacheSettings.

Comprehensive tests for cache configuration and settings.
"""

import pytest

from omnibase_core.models.configuration.model_cache_settings import ModelCacheSettings


class TestModelCacheSettingsInitialization:
    """Test ModelCacheSettings initialization."""

    def test_create_default_cache_settings(self):
        """Test creating cache settings with default values."""
        settings = ModelCacheSettings()
        assert settings is not None
        assert isinstance(settings, ModelCacheSettings)
        assert settings.enabled is True
        assert settings.cache_type == "memory"
        assert settings.default_ttl_seconds == 300

    def test_cache_settings_with_custom_values(self):
        """Test creating cache settings with custom values."""
        settings = ModelCacheSettings(
            enabled=False,
            cache_type="redis",
            default_ttl_seconds=600,
            max_size_mb=200,
        )
        assert settings.enabled is False
        assert settings.cache_type == "redis"
        assert settings.default_ttl_seconds == 600
        assert settings.max_size_mb == 200

    def test_cache_settings_inheritance(self):
        """Test that ModelCacheSettings inherits from BaseModel."""
        from pydantic import BaseModel

        settings = ModelCacheSettings()
        assert isinstance(settings, BaseModel)


class TestModelCacheSettingsValidation:
    """Test ModelCacheSettings field validation."""

    def test_cache_type_validation(self):
        """Test cache_type field validation."""
        # Valid cache types
        for cache_type in ["memory", "redis", "disk"]:
            settings = ModelCacheSettings(cache_type=cache_type)
            assert settings.cache_type == cache_type

    def test_compression_level_validation(self):
        """Test compression_level field constraints."""
        # Valid values
        settings = ModelCacheSettings(compression_level=1)
        assert settings.compression_level == 1

        settings = ModelCacheSettings(compression_level=9)
        assert settings.compression_level == 9

        # Default value
        settings = ModelCacheSettings()
        assert settings.compression_level == 6

    def test_eviction_policy_validation(self):
        """Test eviction_policy field validation."""
        for policy in ["LRU", "LFU", "FIFO"]:
            settings = ModelCacheSettings(eviction_policy=policy)
            assert settings.eviction_policy == policy


class TestModelCacheSettingsSerialization:
    """Test ModelCacheSettings serialization."""

    def test_cache_settings_serialization(self):
        """Test cache settings model_dump."""
        settings = ModelCacheSettings(
            enabled=True,
            cache_type="redis",
            default_ttl_seconds=600,
        )
        data = settings.model_dump()
        assert isinstance(data, dict)
        assert data["enabled"] is True
        assert data["cache_type"] == "redis"
        assert data["default_ttl_seconds"] == 600

    def test_cache_settings_deserialization(self):
        """Test cache settings model_validate."""
        data = {
            "enabled": True,
            "cache_type": "redis",
            "default_ttl_seconds": 600,
        }
        settings = ModelCacheSettings.model_validate(data)
        assert settings.enabled is True
        assert settings.cache_type == "redis"
        assert settings.default_ttl_seconds == 600

    def test_cache_settings_json_serialization(self):
        """Test cache settings JSON serialization."""
        settings = ModelCacheSettings()
        json_data = settings.model_dump_json()
        assert isinstance(json_data, str)
        assert "cache_type" in json_data

    def test_cache_settings_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelCacheSettings(
            cache_type="redis",
            default_ttl_seconds=600,
            max_size_mb=200,
        )
        data = original.model_dump()
        restored = ModelCacheSettings.model_validate(data)
        assert restored.cache_type == original.cache_type
        assert restored.default_ttl_seconds == original.default_ttl_seconds
        assert restored.max_size_mb == original.max_size_mb


class TestModelCacheSettingsMethods:
    """Test ModelCacheSettings methods."""

    def test_get_effective_ttl_with_default(self):
        """Test get_effective_ttl with default TTL."""
        settings = ModelCacheSettings(default_ttl_seconds=300)
        ttl = settings.get_effective_ttl()
        assert ttl == 300

    def test_get_effective_ttl_with_requested(self):
        """Test get_effective_ttl with requested TTL."""
        settings = ModelCacheSettings(default_ttl_seconds=300)
        ttl = settings.get_effective_ttl(requested_ttl=600)
        assert ttl == 600

    def test_get_effective_ttl_with_max_limit(self):
        """Test get_effective_ttl respects max_ttl_seconds."""
        settings = ModelCacheSettings(
            default_ttl_seconds=300,
            max_ttl_seconds=500,
        )
        # Requested TTL exceeds max
        ttl = settings.get_effective_ttl(requested_ttl=1000)
        assert ttl == 500

    def test_get_effective_ttl_when_disabled(self):
        """Test get_effective_ttl returns 0 when disabled."""
        settings = ModelCacheSettings(enabled=False)
        ttl = settings.get_effective_ttl()
        assert ttl == 0

    def test_get_effective_ttl_negative_clamping(self):
        """Test get_effective_ttl clamps negative values to 0."""
        settings = ModelCacheSettings(default_ttl_seconds=300)
        ttl = settings.get_effective_ttl(requested_ttl=-100)
        assert ttl == 0


class TestModelCacheSettingsEdgeCases:
    """Test cache settings edge cases."""

    def test_compression_disabled_by_default(self):
        """Test compression is disabled by default."""
        settings = ModelCacheSettings()
        assert settings.compression_enabled is False

    def test_statistics_enabled_by_default(self):
        """Test statistics tracking is enabled by default."""
        settings = ModelCacheSettings()
        assert settings.track_statistics is True

    def test_invalidation_enabled_by_default(self):
        """Test invalidation is enabled by default."""
        settings = ModelCacheSettings()
        assert settings.invalidation_enabled is True

    def test_invalidation_patterns_default_empty(self):
        """Test invalidation patterns default to empty list."""
        settings = ModelCacheSettings()
        assert settings.invalidation_patterns == []

    def test_key_prefix_none_by_default(self):
        """Test key_prefix is None by default."""
        settings = ModelCacheSettings()
        assert settings.key_prefix is None

    def test_key_hash_algorithm_default(self):
        """Test key_hash_algorithm defaults to sha256."""
        settings = ModelCacheSettings()
        assert settings.key_hash_algorithm == "sha256"

    def test_max_ttl_none_allows_any(self):
        """Test max_ttl_seconds=None allows any TTL."""
        settings = ModelCacheSettings(
            default_ttl_seconds=300,
            max_ttl_seconds=None,
        )
        ttl = settings.get_effective_ttl(requested_ttl=10000)
        assert ttl == 10000


class TestModelCacheSettingsAttributes:
    """Test cache settings attributes and metadata."""

    def test_cache_settings_attributes(self):
        """Test that cache settings has expected attributes."""
        settings = ModelCacheSettings()
        assert hasattr(settings, "model_dump")
        assert callable(settings.model_dump)
        assert hasattr(ModelCacheSettings, "model_validate")
        assert callable(ModelCacheSettings.model_validate)

    def test_cache_settings_docstring(self):
        """Test cache settings docstring."""
        assert ModelCacheSettings.__doc__ is not None
        assert "cache" in ModelCacheSettings.__doc__.lower()

    def test_cache_settings_class_name(self):
        """Test cache settings class name."""
        assert ModelCacheSettings.__name__ == "ModelCacheSettings"

    def test_cache_settings_module(self):
        """Test cache settings module."""
        assert (
            ModelCacheSettings.__module__
            == "omnibase_core.models.configuration.model_cache_settings"
        )

    def test_cache_settings_copy(self):
        """Test cache settings copying."""
        settings = ModelCacheSettings(cache_type="redis")
        copied = settings.model_copy()
        assert copied is not None
        assert copied.cache_type == "redis"
        assert copied is not settings

    def test_cache_settings_equality(self):
        """Test cache settings equality."""
        settings1 = ModelCacheSettings(cache_type="memory")
        settings2 = ModelCacheSettings(cache_type="memory")
        assert settings1 == settings2

    def test_cache_settings_str_repr(self):
        """Test cache settings string representations."""
        settings = ModelCacheSettings()
        str_repr = str(settings)
        assert isinstance(str_repr, str)

        repr_str = repr(settings)
        assert isinstance(repr_str, str)
        assert "ModelCacheSettings" in repr_str
