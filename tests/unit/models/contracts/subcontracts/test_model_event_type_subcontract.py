"""Tests for ModelEventTypeSubcontract - ONEX compliant validators."""

import pytest

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestModelEventTypeSubcontractValidation:
    """Test validation logic for event type subcontract."""

    def test_valid_minimal_subcontract(self) -> None:
        """Test creating a valid minimal subcontract."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
        )

        assert subcontract.primary_events == ["user.created"]
        assert subcontract.event_categories == ["user_management"]
        assert subcontract.event_routing == "default"
        assert subcontract.publish_events is True
        assert subcontract.subscribe_events is False

    def test_interface_version_accessible(self) -> None:
        """Test that INTERFACE_VERSION is accessible and correct."""
        assert hasattr(ModelEventTypeSubcontract, "INTERFACE_VERSION")
        version = ModelEventTypeSubcontract.INTERFACE_VERSION
        assert isinstance(version, ModelSemVer)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert str(version) == "1.0.0"

    def test_empty_primary_events_raises_error(self) -> None:
        """Test that empty primary_events list raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventTypeSubcontract(
                version=DEFAULT_VERSION,
                primary_events=[],
                event_categories=["user_management"],
                event_routing="default",
            )

        assert "primary_events must contain at least one event type" in str(
            exc_info.value,
        )

    def test_empty_event_categories_raises_error(self) -> None:
        """Test that empty event_categories list raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventTypeSubcontract(
                version=DEFAULT_VERSION,
                primary_events=["user.created"],
                event_categories=[],
                event_routing="default",
            )

        assert "event_categories must contain at least one category" in str(
            exc_info.value,
        )

    def test_batch_processing_disabled_allows_any_batch_size(self) -> None:
        """Test that batch_size validation is skipped when batch_processing is False."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            batch_processing=False,
            batch_size=0,  # Invalid if batch_processing were enabled
        )

        assert subcontract.batch_size == 0
        assert subcontract.batch_processing is False

    def test_batch_processing_enabled_with_valid_size(self) -> None:
        """Test batch processing enabled with valid batch size."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            batch_processing=True,
            batch_size=50,
        )

        assert subcontract.batch_processing is True
        assert subcontract.batch_size == 50

    def test_batch_processing_enabled_with_invalid_size_raises_error(self) -> None:
        """Test that batch_size < 1 raises error when batch_processing is enabled."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventTypeSubcontract(
                version=DEFAULT_VERSION,
                primary_events=["user.created"],
                event_categories=["user_management"],
                event_routing="default",
                batch_processing=True,
                batch_size=0,
            )

        assert "batch_size must be positive when batch processing is enabled" in str(
            exc_info.value,
        )

    def test_deduplication_disabled_allows_any_window(self) -> None:
        """Test that deduplication_window_ms validation is skipped when disabled."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            deduplication_enabled=False,
            deduplication_window_ms=500,  # Invalid if enabled
        )

        assert subcontract.deduplication_window_ms == 500
        assert subcontract.deduplication_enabled is False

    def test_deduplication_enabled_with_valid_window(self) -> None:
        """Test deduplication enabled with valid window."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            deduplication_enabled=True,
            deduplication_window_ms=5000,
        )

        assert subcontract.deduplication_enabled is True
        assert subcontract.deduplication_window_ms == 5000

    def test_deduplication_enabled_with_invalid_window_raises_error(self) -> None:
        """Test that window < 1000ms raises error when deduplication is enabled."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventTypeSubcontract(
                version=DEFAULT_VERSION,
                primary_events=["user.created"],
                event_categories=["user_management"],
                event_routing="default",
                deduplication_enabled=True,
                deduplication_window_ms=500,
            )

        assert "deduplication_window_ms must be at least 1000ms when enabled" in str(
            exc_info.value
        )

    def test_full_configuration(self) -> None:
        """Test creating a subcontract with all fields populated."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created", "user.updated"],
            event_categories=["user_management", "audit"],
            publish_events=True,
            subscribe_events=True,
            event_routing="user_routing_group",
            event_filters=["*.user.*", "audit.*"],
            batch_processing=True,
            batch_size=100,
            batch_timeout_ms=5000,
            ordering_required=True,
            delivery_guarantee="exactly_once",
            deduplication_enabled=True,
            deduplication_window_ms=60000,
            async_processing=True,
            max_concurrent_events=50,
            event_metrics_enabled=True,
            event_tracing_enabled=True,
        )

        assert len(subcontract.primary_events) == 2
        assert len(subcontract.event_categories) == 2
        assert subcontract.batch_processing is True
        assert subcontract.batch_size == 100
        assert subcontract.deduplication_enabled is True
        assert subcontract.deduplication_window_ms == 60000


class TestModelEventTypeSubcontractDefaults:
    """Test default values for event type subcontract."""

    def test_default_values(self) -> None:
        """Test that default values are correctly set."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
        )

        # Event behavior defaults
        assert subcontract.publish_events is True
        assert subcontract.subscribe_events is False

        # Batch processing defaults
        assert subcontract.batch_processing is False
        assert subcontract.batch_size == 100
        assert subcontract.batch_timeout_ms == 5000

        # Ordering and delivery defaults
        assert subcontract.ordering_required is False
        assert subcontract.delivery_guarantee == "at_least_once"
        assert subcontract.deduplication_enabled is False
        assert subcontract.deduplication_window_ms == 60000

        # Performance defaults
        assert subcontract.async_processing is True
        assert subcontract.max_concurrent_events == 100
        assert subcontract.event_metrics_enabled is True
        assert subcontract.event_tracing_enabled is False

        # Optional fields defaults
        assert subcontract.event_definitions == []
        assert subcontract.transformations == []
        assert subcontract.routing_config is None
        assert subcontract.persistence_config is None
        assert subcontract.event_filters == []


class TestModelEventTypeSubcontractEdgeCases:
    """Test edge cases for event type subcontract."""

    def test_batch_size_exactly_one_is_valid(self) -> None:
        """Test that batch_size = 1 is valid when batch processing is enabled."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            batch_processing=True,
            batch_size=1,
        )

        assert subcontract.batch_size == 1

    def test_deduplication_window_exactly_1000_is_valid(self) -> None:
        """Test that deduplication_window_ms = 1000 is valid when enabled."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            deduplication_enabled=True,
            deduplication_window_ms=1000,
        )

        assert subcontract.deduplication_window_ms == 1000

    def test_deduplication_window_999_raises_error_when_enabled(self) -> None:
        """Test that deduplication_window_ms = 999 raises error when enabled."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventTypeSubcontract(
                version=DEFAULT_VERSION,
                primary_events=["user.created"],
                event_categories=["user_management"],
                event_routing="default",
                deduplication_enabled=True,
                deduplication_window_ms=999,
            )

        assert "deduplication_window_ms must be at least 1000ms" in str(exc_info.value)

    def test_multiple_primary_events(self) -> None:
        """Test multiple primary events."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created", "user.updated", "user.deleted"],
            event_categories=["user_management"],
            event_routing="default",
        )

        assert len(subcontract.primary_events) == 3

    def test_multiple_event_categories(self) -> None:
        """Test multiple event categories."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management", "audit", "compliance"],
            event_routing="default",
        )

        assert len(subcontract.event_categories) == 3

    def test_max_concurrent_events_boundary_values(self) -> None:
        """Test boundary values for max_concurrent_events."""
        # Test minimum value
        subcontract_min = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            max_concurrent_events=1,
        )
        assert subcontract_min.max_concurrent_events == 1

        # Test high value
        subcontract_high = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            max_concurrent_events=1000,
        )
        assert subcontract_high.max_concurrent_events == 1000

    def test_empty_event_filters_list(self) -> None:
        """Test that empty event_filters list is valid."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            event_filters=[],
        )
        assert subcontract.event_filters == []
        assert len(subcontract.event_filters) == 0

    def test_optional_configs_as_none(self) -> None:
        """Test that optional config fields can be None."""
        subcontract = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            routing_config=None,
            persistence_config=None,
        )
        assert subcontract.routing_config is None
        assert subcontract.persistence_config is None

    def test_batch_timeout_boundary_values(self) -> None:
        """Test boundary values for batch_timeout_ms."""
        # Test low value
        subcontract_low = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            batch_timeout_ms=100,
        )
        assert subcontract_low.batch_timeout_ms == 100

        # Test high value
        subcontract_high = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            batch_timeout_ms=60000,
        )
        assert subcontract_high.batch_timeout_ms == 60000

    def test_all_boolean_flags_combinations(self) -> None:
        """Test various combinations of boolean configuration flags."""
        # All enabled
        subcontract_all = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            publish_events=True,
            subscribe_events=True,
            batch_processing=True,
            ordering_required=True,
            deduplication_enabled=True,
            async_processing=True,
            event_metrics_enabled=True,
            event_tracing_enabled=True,
            batch_size=10,
            deduplication_window_ms=1000,
        )
        assert subcontract_all.publish_events is True
        assert subcontract_all.subscribe_events is True

        # All disabled
        subcontract_none = ModelEventTypeSubcontract(
            version=DEFAULT_VERSION,
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
            publish_events=False,
            subscribe_events=False,
            batch_processing=False,
            ordering_required=False,
            deduplication_enabled=False,
            async_processing=False,
            event_metrics_enabled=False,
            event_tracing_enabled=False,
        )
        assert subcontract_none.publish_events is False
        assert subcontract_none.subscribe_events is False
