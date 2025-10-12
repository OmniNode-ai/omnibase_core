"""Tests for ModelHealthMetadata."""

import pytest

from omnibase_core.models.health.model_health_metadata import ModelHealthMetadata
from omnibase_core.primitives.model_semver import parse_semver_from_string


class TestModelHealthMetadataBasics:
    """Test basic functionality."""

    def test_default_initialization(self):
        """Test default metadata initialization."""
        metadata = ModelHealthMetadata()

        assert metadata.environment == "unknown"
        assert metadata.version == parse_semver_from_string("1.0.0")
        assert metadata.check_interval_seconds == 30
        assert metadata.auto_healing_enabled is True
        assert metadata.maintenance_mode is False
        assert metadata.notification_enabled is True
        assert metadata.escalation_enabled is True
        assert metadata.max_issue_retention_days == 30
        assert metadata.health_score_algorithm == "weighted"

    def test_custom_initialization(self):
        """Test custom metadata initialization."""
        version = parse_semver_from_string("2.1.0")
        metadata = ModelHealthMetadata(
            environment="production",
            version=version,
            check_interval_seconds=60,
            auto_healing_enabled=False,
            maintenance_mode=True,
            notification_enabled=False,
        )

        assert metadata.environment == "production"
        assert metadata.version == version
        assert metadata.check_interval_seconds == 60
        assert metadata.auto_healing_enabled is False
        assert metadata.maintenance_mode is True
        assert metadata.notification_enabled is False


class TestModelHealthMetadataValidation:
    """Test validation."""

    def test_check_interval_validation(self):
        """Test check interval validation."""
        # Valid intervals
        ModelHealthMetadata(check_interval_seconds=1)
        ModelHealthMetadata(check_interval_seconds=3600)

        # Invalid intervals
        with pytest.raises(Exception):
            ModelHealthMetadata(check_interval_seconds=0)
        with pytest.raises(Exception):
            ModelHealthMetadata(check_interval_seconds=3601)

    def test_retention_days_validation(self):
        """Test issue retention days validation."""
        # Valid days
        ModelHealthMetadata(max_issue_retention_days=1)
        ModelHealthMetadata(max_issue_retention_days=365)

        # Invalid days
        with pytest.raises(Exception):
            ModelHealthMetadata(max_issue_retention_days=0)
        with pytest.raises(Exception):
            ModelHealthMetadata(max_issue_retention_days=366)

    def test_algorithm_validation(self):
        """Test health score algorithm validation."""
        # Valid algorithms
        ModelHealthMetadata(health_score_algorithm="simple")
        ModelHealthMetadata(health_score_algorithm="weighted")
        ModelHealthMetadata(health_score_algorithm="custom")

        # Invalid algorithm
        with pytest.raises(Exception):
            ModelHealthMetadata(health_score_algorithm="invalid")


class TestModelHealthMetadataEnvironmentChecking:
    """Test environment checking methods."""

    def test_is_production_environment(self):
        """Test production environment detection."""
        metadata = ModelHealthMetadata(environment="production")
        assert metadata.is_production_environment() is True

        metadata = ModelHealthMetadata(environment="prod")
        assert metadata.is_production_environment() is True

        metadata = ModelHealthMetadata(environment="development")
        assert metadata.is_production_environment() is False

    def test_is_development_environment(self):
        """Test development environment detection."""
        metadata = ModelHealthMetadata(environment="development")
        assert metadata.is_development_environment() is True

        metadata = ModelHealthMetadata(environment="dev")
        assert metadata.is_development_environment() is True

        metadata = ModelHealthMetadata(environment="local")
        assert metadata.is_development_environment() is True

        metadata = ModelHealthMetadata(environment="production")
        assert metadata.is_development_environment() is False


class TestModelHealthMetadataAutoHeal:
    """Test auto-healing logic."""

    def test_should_auto_heal_enabled(self):
        """Test should_auto_heal when enabled."""
        metadata = ModelHealthMetadata(auto_healing_enabled=True, maintenance_mode=False)
        assert metadata.should_auto_heal() is True

    def test_should_auto_heal_disabled(self):
        """Test should_auto_heal when disabled."""
        metadata = ModelHealthMetadata(
            auto_healing_enabled=False, maintenance_mode=False
        )
        assert metadata.should_auto_heal() is False

    def test_should_auto_heal_maintenance(self):
        """Test should_auto_heal during maintenance."""
        metadata = ModelHealthMetadata(auto_healing_enabled=True, maintenance_mode=True)
        assert metadata.should_auto_heal() is False


class TestModelHealthMetadataNotifications:
    """Test notification logic."""

    def test_should_send_notifications_enabled(self):
        """Test should_send_notifications when enabled."""
        metadata = ModelHealthMetadata(
            notification_enabled=True, maintenance_mode=False
        )
        assert metadata.should_send_notifications() is True

    def test_should_send_notifications_disabled(self):
        """Test should_send_notifications when disabled."""
        metadata = ModelHealthMetadata(
            notification_enabled=False, maintenance_mode=False
        )
        assert metadata.should_send_notifications() is False

    def test_should_send_notifications_maintenance(self):
        """Test should_send_notifications during maintenance."""
        metadata = ModelHealthMetadata(
            notification_enabled=True, maintenance_mode=True
        )
        assert metadata.should_send_notifications() is False


class TestModelHealthMetadataCustomAttributes:
    """Test custom attributes management."""

    def test_get_custom_attribute_not_set(self):
        """Test get_custom_attribute when not set."""
        metadata = ModelHealthMetadata()

        result = metadata.get_custom_attribute("nonexistent")
        assert result is None

    def test_get_custom_attribute_with_default(self):
        """Test get_custom_attribute with default value."""
        metadata = ModelHealthMetadata()

        result = metadata.get_custom_attribute("nonexistent", "default_value")
        assert result == "default_value"

    def test_ensure_custom_attributes(self):
        """Test ensure_custom_attributes creates attributes."""
        metadata = ModelHealthMetadata()

        attrs = metadata.ensure_custom_attributes()
        assert attrs is not None
        assert metadata.custom_attributes is not None


class TestModelHealthMetadataCheckInterval:
    """Test check interval methods."""

    def test_get_effective_check_interval_normal(self):
        """Test effective check interval in normal mode."""
        metadata = ModelHealthMetadata(
            check_interval_seconds=30, maintenance_mode=False
        )

        assert metadata.get_effective_check_interval() == 30

    def test_get_effective_check_interval_maintenance(self):
        """Test effective check interval in maintenance mode."""
        metadata = ModelHealthMetadata(
            check_interval_seconds=30, maintenance_mode=True
        )

        # Should be 3x longer in maintenance, up to 300 max
        assert metadata.get_effective_check_interval() == 90

    def test_get_effective_check_interval_maintenance_capped(self):
        """Test effective check interval caps at 300."""
        metadata = ModelHealthMetadata(
            check_interval_seconds=200, maintenance_mode=True
        )

        # Should cap at 300
        assert metadata.get_effective_check_interval() == 300


class TestModelHealthMetadataFactoryMethods:
    """Test factory methods."""

    def test_create_production(self):
        """Test production metadata factory."""
        metadata = ModelHealthMetadata.create_production()

        assert metadata.environment == "production"
        assert metadata.check_interval_seconds == 30
        assert metadata.auto_healing_enabled is True
        assert metadata.notification_enabled is True
        assert metadata.escalation_enabled is True

    def test_create_production_with_additional_args(self):
        """Test production metadata with additional args."""
        metadata = ModelHealthMetadata.create_production(max_issue_retention_days=60)

        assert metadata.environment == "production"
        assert metadata.max_issue_retention_days == 60

    def test_create_development(self):
        """Test development metadata factory."""
        metadata = ModelHealthMetadata.create_development()

        assert metadata.environment == "development"
        assert metadata.check_interval_seconds == 60
        assert metadata.auto_healing_enabled is False
        assert metadata.notification_enabled is False
        assert metadata.escalation_enabled is False

    def test_create_development_with_additional_args(self):
        """Test development metadata with additional args."""
        metadata = ModelHealthMetadata.create_development(max_issue_retention_days=15)

        assert metadata.environment == "development"
        assert metadata.max_issue_retention_days == 15

    def test_create_maintenance_mode(self):
        """Test maintenance mode metadata factory."""
        metadata = ModelHealthMetadata.create_maintenance_mode()

        assert metadata.maintenance_mode is True
        assert metadata.auto_healing_enabled is False
        assert metadata.notification_enabled is False
        assert metadata.check_interval_seconds == 120

    def test_create_maintenance_mode_with_additional_args(self):
        """Test maintenance mode metadata with additional args."""
        metadata = ModelHealthMetadata.create_maintenance_mode(escalation_enabled=True)

        assert metadata.maintenance_mode is True
        assert metadata.escalation_enabled is True
