"""Tests for ModelEventTypeSubcontract - ONEX compliant validators."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelEventTypeSubcontractValidation:
    """Test validation logic for event type subcontract."""

    def test_valid_minimal_subcontract(self) -> None:
        """Test creating a valid minimal subcontract."""
        subcontract = ModelEventTypeSubcontract(
            primary_events=["user.created"],
            event_categories=["user_management"],
            event_routing="default",
        )

        assert subcontract.primary_events == ["user.created"]
        assert subcontract.event_categories == ["user_management"]
        assert subcontract.event_routing == "default"
        assert subcontract.publish_events is True
        assert subcontract.subscribe_events is False

    def test_empty_primary_events_raises_error(self) -> None:
        """Test that empty primary_events list raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventTypeSubcontract(
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
            primary_events=["user.created", "user.updated", "user.deleted"],
            event_categories=["user_management"],
            event_routing="default",
        )

        assert len(subcontract.primary_events) == 3

    def test_multiple_event_categories(self) -> None:
        """Test multiple event categories."""
        subcontract = ModelEventTypeSubcontract(
            primary_events=["user.created"],
            event_categories=["user_management", "audit", "compliance"],
            event_routing="default",
        )

        assert len(subcontract.event_categories) == 3
