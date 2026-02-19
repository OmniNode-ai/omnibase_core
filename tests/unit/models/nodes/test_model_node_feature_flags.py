# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelNodeFeatureFlags.

Tests all aspects of the node feature flags model including:
- Model instantiation with defaults and custom values
- Feature management methods
- Feature summary generation
- Production/debug mode checks
- Factory methods
- Protocol implementations
- Edge cases
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.node_metadata.model_node_feature_flags import (
    ModelNodeFeatureFlags,
)


@pytest.mark.unit
class TestModelNodeFeatureFlags:
    """Test cases for ModelNodeFeatureFlags."""

    def test_model_instantiation_default(self):
        """Test that model can be instantiated with defaults."""
        flags = ModelNodeFeatureFlags()

        assert flags.enable_caching is False
        assert flags.enable_monitoring is True
        assert flags.enable_tracing is False

    def test_model_instantiation_custom(self):
        """Test model instantiation with custom values."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=False,
            enable_tracing=True,
        )

        assert flags.enable_caching is True
        assert flags.enable_monitoring is False
        assert flags.enable_tracing is True

    def test_get_enabled_features_all_enabled(self):
        """Test get_enabled_features when all features enabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=True,
        )

        enabled = flags.get_enabled_features()
        assert len(enabled) == 3
        assert "caching" in enabled
        assert "monitoring" in enabled
        assert "tracing" in enabled

    def test_get_enabled_features_none_enabled(self):
        """Test get_enabled_features when no features enabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=False,
            enable_monitoring=False,
            enable_tracing=False,
        )

        enabled = flags.get_enabled_features()
        assert len(enabled) == 0

    def test_get_enabled_features_partial(self):
        """Test get_enabled_features with some features enabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=False,
            enable_tracing=True,
        )

        enabled = flags.get_enabled_features()
        assert len(enabled) == 2
        assert "caching" in enabled
        assert "tracing" in enabled
        assert "monitoring" not in enabled

    def test_get_disabled_features_all_disabled(self):
        """Test get_disabled_features when all features disabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=False,
            enable_monitoring=False,
            enable_tracing=False,
        )

        disabled = flags.get_disabled_features()
        assert len(disabled) == 3
        assert "caching" in disabled
        assert "monitoring" in disabled
        assert "tracing" in disabled

    def test_get_disabled_features_none_disabled(self):
        """Test get_disabled_features when all features enabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=True,
        )

        disabled = flags.get_disabled_features()
        assert len(disabled) == 0

    def test_get_disabled_features_partial(self):
        """Test get_disabled_features with some features disabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=False,
            enable_monitoring=True,
            enable_tracing=False,
        )

        disabled = flags.get_disabled_features()
        assert len(disabled) == 2
        assert "caching" in disabled
        assert "tracing" in disabled
        assert "monitoring" not in disabled

    def test_get_feature_summary_all_enabled(self):
        """Test get_feature_summary with all features enabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=True,
        )

        summary = flags.get_feature_summary()
        assert summary["enable_caching"] == "True"
        assert summary["enable_monitoring"] == "True"
        assert summary["enable_tracing"] == "True"
        assert summary["enabled_count"] == "3"
        assert "caching" in summary["enabled_features"]
        assert summary["is_monitoring_enabled"] == "True"
        assert summary["is_debug_mode"] == "True"

    def test_get_feature_summary_none_enabled(self):
        """Test get_feature_summary with no features enabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=False,
            enable_monitoring=False,
            enable_tracing=False,
        )

        summary = flags.get_feature_summary()
        assert summary["enabled_features"] == "none"
        assert summary["enabled_count"] == "0"
        assert summary["is_monitoring_enabled"] == "False"
        assert summary["is_debug_mode"] == "False"

    def test_get_feature_summary_partial(self):
        """Test get_feature_summary with some features enabled."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=False,
        )

        summary = flags.get_feature_summary()
        assert summary["enabled_count"] == "2"
        assert "caching" in summary["enabled_features"]
        assert "monitoring" in summary["enabled_features"]

    def test_is_production_ready_true(self):
        """Test is_production_ready returns True for production config."""
        flags = ModelNodeFeatureFlags(
            enable_monitoring=True,
            enable_tracing=False,
        )

        assert flags.is_production_ready() is True

    def test_is_production_ready_false_no_monitoring(self):
        """Test is_production_ready returns False without monitoring."""
        flags = ModelNodeFeatureFlags(
            enable_monitoring=False,
            enable_tracing=False,
        )

        assert flags.is_production_ready() is False

    def test_is_production_ready_false_with_tracing(self):
        """Test is_production_ready returns False with tracing enabled."""
        flags = ModelNodeFeatureFlags(
            enable_monitoring=True,
            enable_tracing=True,
        )

        assert flags.is_production_ready() is False

    def test_is_debug_mode_true(self):
        """Test is_debug_mode returns True when tracing enabled."""
        flags = ModelNodeFeatureFlags(enable_tracing=True)

        assert flags.is_debug_mode() is True

    def test_is_debug_mode_false(self):
        """Test is_debug_mode returns False when tracing disabled."""
        flags = ModelNodeFeatureFlags(enable_tracing=False)

        assert flags.is_debug_mode() is False

    def test_enable_all_features(self):
        """Test enable_all_features method."""
        flags = ModelNodeFeatureFlags()

        flags.enable_all_features()

        assert flags.enable_caching is True
        assert flags.enable_monitoring is True
        assert flags.enable_tracing is True

    def test_disable_all_features(self):
        """Test disable_all_features method."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=True,
        )

        flags.disable_all_features()

        assert flags.enable_caching is False
        assert flags.enable_monitoring is False
        assert flags.enable_tracing is False

    def test_create_production_factory(self):
        """Test create_production factory method."""
        flags = ModelNodeFeatureFlags.create_production()

        assert flags.enable_caching is True
        assert flags.enable_monitoring is True
        assert flags.enable_tracing is False
        assert flags.is_production_ready() is True

    def test_create_development_factory(self):
        """Test create_development factory method."""
        flags = ModelNodeFeatureFlags.create_development()

        assert flags.enable_caching is False
        assert flags.enable_monitoring is True
        assert flags.enable_tracing is True
        assert flags.is_debug_mode() is True


@pytest.mark.unit
class TestModelNodeFeatureFlagsProtocols:
    """Test protocol implementations."""

    def test_get_id_protocol_raises_error(self):
        """Test get_id protocol method raises error (no ID field)."""
        flags = ModelNodeFeatureFlags()

        with pytest.raises(ModelOnexError) as exc_info:
            flags.get_id()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must have a valid ID field" in str(exc_info.value)

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        flags = ModelNodeFeatureFlags()

        metadata = flags.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        flags = ModelNodeFeatureFlags()

        result = flags.set_metadata({"enable_caching": True})
        assert result is True
        assert flags.enable_caching is True

    def test_set_metadata_protocol_unknown_field(self):
        """Test set_metadata with unknown field."""
        flags = ModelNodeFeatureFlags()

        result = flags.set_metadata({"unknown_field": "value"})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        flags = ModelNodeFeatureFlags()

        serialized = flags.serialize()
        assert isinstance(serialized, dict)
        assert "enable_caching" in serialized
        assert "enable_monitoring" in serialized
        assert "enable_tracing" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        flags = ModelNodeFeatureFlags()

        assert flags.validate_instance() is True


@pytest.mark.unit
class TestModelNodeFeatureFlagsEdgeCases:
    """Test edge cases and error scenarios."""

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        flags = ModelNodeFeatureFlags(extra_field="ignored")

        assert flags.enable_caching is False

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        flags = ModelNodeFeatureFlags()

        flags.enable_caching = True
        assert flags.enable_caching is True

    def test_toggle_features_dynamically(self):
        """Test toggling features dynamically."""
        flags = ModelNodeFeatureFlags()

        # Enable caching
        flags.enable_caching = True
        assert "caching" in flags.get_enabled_features()

        # Disable caching
        flags.enable_caching = False
        assert "caching" not in flags.get_enabled_features()

    def test_feature_summary_updates_with_changes(self):
        """Test feature summary reflects changes."""
        flags = ModelNodeFeatureFlags()

        summary1 = flags.get_feature_summary()
        assert summary1["enabled_count"] == "1"  # Only monitoring

        flags.enable_all_features()
        summary2 = flags.get_feature_summary()
        assert summary2["enabled_count"] == "3"

    def test_production_ready_changes_with_flags(self):
        """Test production_ready status changes with flags."""
        flags = ModelNodeFeatureFlags.create_production()

        assert flags.is_production_ready() is True

        flags.enable_tracing = True
        assert flags.is_production_ready() is False

        flags.enable_tracing = False
        assert flags.is_production_ready() is True

    def test_serialize_includes_all_fields(self):
        """Test serialize includes all fields."""
        flags = ModelNodeFeatureFlags()

        serialized = flags.serialize()

        expected_fields = ["enable_caching", "enable_monitoring", "enable_tracing"]

        for field in expected_fields:
            assert field in serialized

    def test_enabled_and_disabled_are_complements(self):
        """Test enabled and disabled features are complements."""
        flags = ModelNodeFeatureFlags(
            enable_caching=True,
            enable_monitoring=False,
            enable_tracing=True,
        )

        enabled = set(flags.get_enabled_features())
        disabled = set(flags.get_disabled_features())

        # No overlap
        assert len(enabled & disabled) == 0

        # Together they cover all features
        all_features = {"caching", "monitoring", "tracing"}
        assert (enabled | disabled) == all_features
