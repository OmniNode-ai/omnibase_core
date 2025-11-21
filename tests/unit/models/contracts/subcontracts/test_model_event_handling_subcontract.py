"""
Unit tests for ModelEventHandlingSubcontract.

Tests comprehensive event handling subcontract configuration including:
- Event subscription and filtering
- Introspection and discovery handling
- Retry and resilience configuration
- Dead letter queue settings
- Event handler lifecycle management
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.subcontracts.model_event_handling_subcontract import (
    ModelEventHandlingSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestModelEventHandlingSubcontractBasics:
    """Test basic functionality of ModelEventHandlingSubcontract."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        subcontract = ModelEventHandlingSubcontract()

        assert subcontract.enabled is True
        assert subcontract.subscribed_events == [
            "NODE_INTROSPECTION_REQUEST",
            "NODE_DISCOVERY_REQUEST",
        ]
        assert subcontract.auto_subscribe_on_init is True
        assert subcontract.event_filters == {}
        assert subcontract.enable_node_id_filtering is True
        assert subcontract.enable_node_name_filtering is True
        assert subcontract.respond_to_all_when_no_filter is True

    def test_interface_version(self) -> None:
        """Test interface version is set correctly."""
        assert (
            ModelSemVer(major=1, minor=0, patch=0)
            == ModelEventHandlingSubcontract.INTERFACE_VERSION
        )

    def test_minimal_instantiation(self) -> None:
        """Test minimal valid instantiation."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            subscribed_events=["NODE_INTROSPECTION_REQUEST"],
        )

        assert subcontract.enabled is True
        assert subcontract.subscribed_events == ["NODE_INTROSPECTION_REQUEST"]

    def test_full_instantiation(self) -> None:
        """Test full instantiation with all fields."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            subscribed_events=["NODE_INTROSPECTION_REQUEST", "CUSTOM_EVENT"],
            auto_subscribe_on_init=True,
            event_filters={"node_id": "compute*"},
            enable_node_id_filtering=True,
            enable_node_name_filtering=True,
            respond_to_all_when_no_filter=True,
            handle_introspection_requests=True,
            handle_discovery_requests=True,
            filter_introspection_data=True,
            async_event_bus_support=True,
            sync_event_bus_fallback=True,
            cleanup_on_shutdown=True,
            max_retries=5,
            retry_delay_seconds=2.0,
            retry_exponential_backoff=True,
            dead_letter_channel="dlq.events.failed",
            dead_letter_max_events=500,
            dead_letter_overflow_strategy="drop_oldest",
            fail_fast_on_handler_errors=False,
            log_handler_errors=True,
            emit_error_events=True,
            track_handler_performance=True,
            handler_timeout_seconds=30.0,
        )

        assert subcontract.enabled is True
        assert len(subcontract.subscribed_events) == 2
        assert subcontract.max_retries == 5
        assert subcontract.retry_delay_seconds == 2.0
        assert subcontract.dead_letter_channel == "dlq.events.failed"


class TestModelEventHandlingSubcontractSubscribedEvents:
    """Test subscribed_events field validation."""

    def test_subscribed_events_cannot_be_empty(self) -> None:
        """Test that subscribed_events cannot be empty list."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventHandlingSubcontract(
                enabled=True,
                subscribed_events=[],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "cannot be empty" in exc_info.value.message

    def test_subscribed_events_with_wildcards(self) -> None:
        """Test subscribed_events with wildcard patterns."""
        subcontract = ModelEventHandlingSubcontract(
            subscribed_events=["*.discovery.*", "core.introspection.*"],
        )

        assert "*.discovery.*" in subcontract.subscribed_events
        assert "core.introspection.*" in subcontract.subscribed_events

    def test_subscribed_events_single_event(self) -> None:
        """Test subscribed_events with single event."""
        subcontract = ModelEventHandlingSubcontract(
            subscribed_events=["CUSTOM_EVENT"],
        )

        assert subcontract.subscribed_events == ["CUSTOM_EVENT"]


class TestModelEventHandlingSubcontractDeadLetterChannel:
    """Test dead_letter_channel field validation."""

    def test_dead_letter_channel_valid_names(self) -> None:
        """Test valid dead letter channel names."""
        valid_names = [
            "dlq.events",
            "dead_letter_queue",
            "events-failed",
            "dlq_events_123",
        ]

        for name in valid_names:
            subcontract = ModelEventHandlingSubcontract(
                dead_letter_channel=name,
            )
            assert subcontract.dead_letter_channel == name

    def test_dead_letter_channel_invalid_names(self) -> None:
        """Test invalid dead letter channel names."""
        invalid_names = [
            "dlq events",  # Space
            "dlq/events",  # Slash
            "dlq@events",  # Special char
        ]

        for name in invalid_names:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelEventHandlingSubcontract(
                    dead_letter_channel=name,
                )

            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_dead_letter_channel_none(self) -> None:
        """Test dead_letter_channel can be None."""
        subcontract = ModelEventHandlingSubcontract(
            dead_letter_channel=None,
        )

        assert subcontract.dead_letter_channel is None


class TestModelEventHandlingSubcontractOverflowStrategy:
    """Test dead_letter_overflow_strategy validation."""

    def test_overflow_strategy_valid_values(self) -> None:
        """Test valid overflow strategy values."""
        valid_strategies = ["drop_oldest", "drop_newest", "block"]

        for strategy in valid_strategies:
            subcontract = ModelEventHandlingSubcontract(
                dead_letter_overflow_strategy=strategy,
            )
            assert subcontract.dead_letter_overflow_strategy == strategy

    def test_overflow_strategy_invalid_value(self) -> None:
        """Test invalid overflow strategy value."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventHandlingSubcontract(
                dead_letter_overflow_strategy="invalid_strategy",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be one of" in exc_info.value.message


class TestModelEventHandlingSubcontractRetryConfiguration:
    """Test retry configuration validation."""

    def test_retry_delay_must_be_positive_when_retries_enabled(self) -> None:
        """Test retry_delay_seconds must be >= 0.1 (Pydantic field constraint)."""
        from pydantic import ValidationError

        # Pydantic field constraint catches this before model validator
        with pytest.raises(ValidationError) as exc_info:
            ModelEventHandlingSubcontract(
                max_retries=3,
                retry_delay_seconds=0.0,
            )

        assert "greater than or equal to 0.1" in str(exc_info.value)

    def test_retry_delay_can_be_zero_when_retries_disabled(self) -> None:
        """Test retry_delay_seconds can be 0 when max_retries = 0."""
        # This should pass validation since max_retries is 0
        subcontract = ModelEventHandlingSubcontract(
            max_retries=0,
            retry_delay_seconds=0.1,  # Min value from Field constraint
        )

        assert subcontract.max_retries == 0

    def test_max_retries_range(self) -> None:
        """Test max_retries respects range constraints."""
        # Valid range
        subcontract = ModelEventHandlingSubcontract(max_retries=5)
        assert subcontract.max_retries == 5

        # Upper bound
        subcontract = ModelEventHandlingSubcontract(max_retries=10)
        assert subcontract.max_retries == 10

        # Lower bound
        subcontract = ModelEventHandlingSubcontract(max_retries=0)
        assert subcontract.max_retries == 0

    def test_exponential_backoff_configuration(self) -> None:
        """Test exponential backoff configuration."""
        subcontract = ModelEventHandlingSubcontract(
            max_retries=5,
            retry_delay_seconds=1.0,
            retry_exponential_backoff=True,
        )

        assert subcontract.retry_exponential_backoff is True
        assert subcontract.max_retries == 5


class TestModelEventHandlingSubcontractHandlerTimeout:
    """Test handler_timeout_seconds validation."""

    def test_handler_timeout_minimum_value(self) -> None:
        """Test handler_timeout_seconds must be >= 1.0 when specified."""
        from pydantic import ValidationError

        # Pydantic field constraint catches this before model validator
        with pytest.raises(ValidationError) as exc_info:
            ModelEventHandlingSubcontract(
                handler_timeout_seconds=0.5,
            )

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_handler_timeout_valid_values(self) -> None:
        """Test valid handler_timeout_seconds values."""
        valid_timeouts = [1.0, 30.0, 60.0, 300.0]

        for timeout in valid_timeouts:
            subcontract = ModelEventHandlingSubcontract(
                handler_timeout_seconds=timeout,
            )
            assert subcontract.handler_timeout_seconds == timeout

    def test_handler_timeout_none(self) -> None:
        """Test handler_timeout_seconds can be None."""
        subcontract = ModelEventHandlingSubcontract(
            handler_timeout_seconds=None,
        )

        assert subcontract.handler_timeout_seconds is None


class TestModelEventHandlingSubcontractDLQMaxEvents:
    """Test dead_letter_max_events validation."""

    def test_dlq_max_events_warning_threshold(self) -> None:
        """Test warning when dead_letter_max_events exceeds 5000."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventHandlingSubcontract(
                dead_letter_max_events=6000,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "may cause memory issues" in exc_info.value.message

    def test_dlq_max_events_valid_range(self) -> None:
        """Test valid dead_letter_max_events values."""
        valid_values = [10, 100, 1000, 5000]

        for value in valid_values:
            subcontract = ModelEventHandlingSubcontract(
                dead_letter_max_events=value,
            )
            assert subcontract.dead_letter_max_events == value


class TestModelEventHandlingSubcontractAsyncSyncConfiguration:
    """Test async/sync event bus configuration."""

    def test_both_async_and_sync_disabled_fails(self) -> None:
        """Test that at least one of async or sync must be enabled."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventHandlingSubcontract(
                async_event_bus_support=False,
                sync_event_bus_fallback=False,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "At least one of" in exc_info.value.message

    def test_async_only_configuration(self) -> None:
        """Test async-only configuration."""
        subcontract = ModelEventHandlingSubcontract(
            async_event_bus_support=True,
            sync_event_bus_fallback=False,
        )

        assert subcontract.async_event_bus_support is True
        assert subcontract.sync_event_bus_fallback is False

    def test_sync_only_configuration(self) -> None:
        """Test sync-only configuration."""
        subcontract = ModelEventHandlingSubcontract(
            async_event_bus_support=False,
            sync_event_bus_fallback=True,
        )

        assert subcontract.async_event_bus_support is False
        assert subcontract.sync_event_bus_fallback is True

    def test_both_async_and_sync_enabled(self) -> None:
        """Test both async and sync enabled (default)."""
        subcontract = ModelEventHandlingSubcontract()

        assert subcontract.async_event_bus_support is True
        assert subcontract.sync_event_bus_fallback is True


class TestModelEventHandlingSubcontractEventFilters:
    """Test event_filters field."""

    def test_event_filters_empty_dict(self) -> None:
        """Test event_filters with empty dict."""
        subcontract = ModelEventHandlingSubcontract(
            event_filters={},
        )

        assert subcontract.event_filters == {}

    def test_event_filters_with_node_id(self) -> None:
        """Test event_filters with node_id pattern."""
        subcontract = ModelEventHandlingSubcontract(
            event_filters={"node_id": "compute*"},
        )

        assert subcontract.event_filters["node_id"] == "compute*"

    def test_event_filters_with_node_name(self) -> None:
        """Test event_filters with node_name pattern."""
        subcontract = ModelEventHandlingSubcontract(
            event_filters={"node_name": "node_*_effect"},
        )

        assert subcontract.event_filters["node_name"] == "node_*_effect"

    def test_event_filters_with_custom_fields(self) -> None:
        """Test event_filters with custom fields."""
        subcontract = ModelEventHandlingSubcontract(
            event_filters={
                "node_id": "compute*",
                "event_source": "external",
                "priority": "high",
            },
        )

        assert len(subcontract.event_filters) == 3
        assert subcontract.event_filters["priority"] == "high"


class TestModelEventHandlingSubcontractConfigDict:
    """Test model_config settings."""

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert subcontract.enabled is True
        assert not hasattr(subcontract, "unknown_field")

    def test_validate_assignment(self) -> None:
        """Test that assignment validation is enabled."""
        subcontract = ModelEventHandlingSubcontract()

        # Valid assignment
        subcontract.max_retries = 5
        assert subcontract.max_retries == 5


class TestModelEventHandlingSubcontractSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump(self) -> None:
        """Test model serialization."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            subscribed_events=["CUSTOM_EVENT"],
            max_retries=5,
        )

        data = subcontract.model_dump()

        assert data["enabled"] is True
        assert data["subscribed_events"] == ["CUSTOM_EVENT"]
        assert data["max_retries"] == 5

    def test_model_dump_json(self) -> None:
        """Test JSON serialization."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            dead_letter_channel="dlq.events",
        )

        json_str = subcontract.model_dump_json()

        assert isinstance(json_str, str)
        assert "dlq.events" in json_str

    def test_model_validate(self) -> None:
        """Test model deserialization."""
        data = {
            "enabled": True,
            "subscribed_events": ["NODE_INTROSPECTION_REQUEST"],
            "max_retries": 3,
            "retry_delay_seconds": 1.0,
        }

        subcontract = ModelEventHandlingSubcontract.model_validate(data)

        assert subcontract.enabled is True
        assert subcontract.max_retries == 3


class TestModelEventHandlingSubcontractEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_retries_boundary_values(self) -> None:
        """Test max_retries at boundary values."""
        # Lower bound
        subcontract = ModelEventHandlingSubcontract(max_retries=0)
        assert subcontract.max_retries == 0

        # Upper bound
        subcontract = ModelEventHandlingSubcontract(max_retries=10)
        assert subcontract.max_retries == 10

    def test_retry_delay_boundary_values(self) -> None:
        """Test retry_delay_seconds at boundary values."""
        # Lower bound
        subcontract = ModelEventHandlingSubcontract(
            max_retries=0,  # Required to pass validation
            retry_delay_seconds=0.1,
        )
        assert subcontract.retry_delay_seconds == 0.1

        # Upper bound
        subcontract = ModelEventHandlingSubcontract(
            retry_delay_seconds=60.0,
        )
        assert subcontract.retry_delay_seconds == 60.0

    def test_disabled_event_handling(self) -> None:
        """Test event handling can be disabled."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=False,
        )

        assert subcontract.enabled is False

    def test_all_features_disabled(self) -> None:
        """Test configuration with most features disabled."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=False,
            auto_subscribe_on_init=False,
            handle_introspection_requests=False,
            handle_discovery_requests=False,
            filter_introspection_data=False,
            cleanup_on_shutdown=False,
            max_retries=0,
            retry_exponential_backoff=False,
            fail_fast_on_handler_errors=False,
            log_handler_errors=False,
            emit_error_events=False,
            track_handler_performance=False,
        )

        assert subcontract.enabled is False
        assert subcontract.max_retries == 0


class TestModelEventHandlingSubcontractUseCases:
    """Test realistic use cases."""

    def test_minimal_event_handler_configuration(self) -> None:
        """Test minimal event handler configuration."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            subscribed_events=["NODE_INTROSPECTION_REQUEST"],
            max_retries=0,
        )

        assert subcontract.enabled is True
        assert subcontract.max_retries == 0

    def test_production_event_handler_configuration(self) -> None:
        """Test production-grade event handler configuration."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            subscribed_events=["NODE_INTROSPECTION_REQUEST", "NODE_DISCOVERY_REQUEST"],
            event_filters={"node_id": "prod-*"},
            max_retries=5,
            retry_delay_seconds=2.0,
            retry_exponential_backoff=True,
            dead_letter_channel="dlq.events.prod",
            dead_letter_max_events=1000,
            handler_timeout_seconds=60.0,
            track_handler_performance=True,
        )

        assert subcontract.max_retries == 5
        assert subcontract.dead_letter_channel == "dlq.events.prod"
        assert subcontract.handler_timeout_seconds == 60.0

    def test_high_throughput_configuration(self) -> None:
        """Test high-throughput event handler configuration."""
        subcontract = ModelEventHandlingSubcontract(
            enabled=True,
            subscribed_events=["*.events.*"],
            max_retries=1,  # Fast fail for high throughput
            retry_delay_seconds=0.1,
            dead_letter_max_events=5000,
            handler_timeout_seconds=1.0,  # Short timeout
            fail_fast_on_handler_errors=True,
        )

        assert subcontract.max_retries == 1
        assert subcontract.handler_timeout_seconds == 1.0
        assert subcontract.fail_fast_on_handler_errors is True


class TestModelEventHandlingSubcontractDocumentation:
    """Test documentation and metadata."""

    def test_docstring_present(self) -> None:
        """Test that class has comprehensive docstring."""
        assert ModelEventHandlingSubcontract.__doc__ is not None
        assert "Event Handling subcontract" in ModelEventHandlingSubcontract.__doc__

    def test_field_descriptions(self) -> None:
        """Test that all fields have descriptions."""
        fields = ModelEventHandlingSubcontract.model_fields

        for field_name, field_info in fields.items():
            assert (
                field_info.description is not None
            ), f"Field {field_name} missing description"
            assert (
                len(field_info.description) > 0
            ), f"Field {field_name} has empty description"
