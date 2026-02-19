# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEventBusSubcontract.

Comprehensive tests for event bus subcontract configuration and validation.
"""

import pytest

from omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract import (
    ModelEventBusSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelEventBusSubcontractInitialization:
    """Test ModelEventBusSubcontract initialization."""

    def test_create_default_event_bus_subcontract(self):
        """Test creating event bus subcontract with default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract is not None
        assert isinstance(subcontract, ModelEventBusSubcontract)
        assert subcontract.event_bus_enabled is True
        assert subcontract.event_bus_type == "hybrid"
        assert subcontract.enable_event_logging is True
        assert subcontract.correlation_tracking is True
        assert subcontract.max_queue_size == 10000
        assert subcontract.batch_size == 100

    def test_event_bus_subcontract_with_custom_values(self):
        """Test creating event bus subcontract with custom values."""
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            event_bus_enabled=False,
            event_bus_type="memory",
            enable_event_logging=False,
            correlation_tracking=False,
            max_queue_size=5000,
            batch_size=50,
        )
        assert subcontract.event_bus_enabled is False
        assert subcontract.event_bus_type == "memory"
        assert subcontract.enable_event_logging is False
        assert subcontract.correlation_tracking is False
        assert subcontract.max_queue_size == 5000
        assert subcontract.batch_size == 50

    def test_event_bus_subcontract_inheritance(self):
        """Test that ModelEventBusSubcontract inherits from BaseModel."""
        from pydantic import BaseModel

        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert isinstance(subcontract, BaseModel)

    def test_interface_version_accessible(self):
        """Test that INTERFACE_VERSION is accessible as ClassVar."""
        assert hasattr(ModelEventBusSubcontract, "INTERFACE_VERSION")
        version = ModelEventBusSubcontract.INTERFACE_VERSION
        assert isinstance(version, ModelSemVer)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0


@pytest.mark.unit
class TestModelEventBusSubcontractValidation:
    """Test ModelEventBusSubcontract field validation."""

    def test_event_bus_type_valid_values(self):
        """Test event_bus_type accepts valid values."""
        for bus_type in ["memory", "hybrid", "distributed"]:
            subcontract = ModelEventBusSubcontract(
                version=DEFAULT_VERSION, event_bus_type=bus_type
            )
            assert subcontract.event_bus_type == bus_type

    def test_event_bus_type_invalid_value_raises_error(self):
        """Test event_bus_type rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventBusSubcontract(version=DEFAULT_VERSION, event_bus_type="invalid")
        assert "event_bus_type must be one of" in str(exc_info.value)

    def test_queue_overflow_strategy_valid_values(self):
        """Test queue_overflow_strategy accepts valid values."""
        for strategy in ["block", "drop_oldest", "drop_newest"]:
            subcontract = ModelEventBusSubcontract(
                version=DEFAULT_VERSION, queue_overflow_strategy=strategy
            )
            assert subcontract.queue_overflow_strategy == strategy

    def test_queue_overflow_strategy_invalid_value_raises_error(self):
        """Test queue_overflow_strategy rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventBusSubcontract(
                version=DEFAULT_VERSION, queue_overflow_strategy="invalid"
            )
        assert "queue_overflow_strategy must be one of" in str(exc_info.value)

    def test_max_queue_size_constraints(self):
        """Test max_queue_size field constraints."""
        # Valid values
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, max_queue_size=100
        )
        assert subcontract.max_queue_size == 100

        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, max_queue_size=50000
        )
        assert subcontract.max_queue_size == 50000

        # Exceeds safety threshold
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventBusSubcontract(version=DEFAULT_VERSION, max_queue_size=60000)
        assert "max_queue_size exceeding 50000 may cause memory issues" in str(
            exc_info.value,
        )

    def test_batch_size_constraints(self):
        """Test batch_size field constraints."""
        # Valid values
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION, batch_size=1)
        assert subcontract.batch_size == 1

        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION, batch_size=500)
        assert subcontract.batch_size == 500

        # Exceeds recommended threshold
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEventBusSubcontract(version=DEFAULT_VERSION, batch_size=600)
        assert "batch_size exceeding 500 may cause performance degradation" in str(
            exc_info.value,
        )

    def test_max_retry_attempts_constraints(self):
        """Test max_retry_attempts field constraints."""
        # Valid values
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, max_retry_attempts=1
        )
        assert subcontract.max_retry_attempts == 1

        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, max_retry_attempts=10
        )
        assert subcontract.max_retry_attempts == 10

    def test_batch_timeout_ms_constraints(self):
        """Test batch_timeout_ms field constraints."""
        # Valid values
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, batch_timeout_ms=100
        )
        assert subcontract.batch_timeout_ms == 100

        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, batch_timeout_ms=60000
        )
        assert subcontract.batch_timeout_ms == 60000


@pytest.mark.unit
class TestModelEventBusSubcontractSerialization:
    """Test ModelEventBusSubcontract serialization."""

    def test_event_bus_subcontract_serialization(self):
        """Test event bus subcontract model_dump."""
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            event_bus_enabled=True,
            event_bus_type="distributed",
            max_queue_size=15000,
            batch_size=200,
        )
        data = subcontract.model_dump()
        assert isinstance(data, dict)
        assert data["event_bus_enabled"] is True
        assert data["event_bus_type"] == "distributed"
        assert data["max_queue_size"] == 15000
        assert data["batch_size"] == 200

    def test_event_bus_subcontract_deserialization(self):
        """Test event bus subcontract model_validate."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "event_bus_enabled": True,
            "event_bus_type": "memory",
            "max_queue_size": 5000,
            "batch_size": 50,
        }
        subcontract = ModelEventBusSubcontract.model_validate(data)
        assert subcontract.event_bus_enabled is True
        assert subcontract.event_bus_type == "memory"
        assert subcontract.max_queue_size == 5000
        assert subcontract.batch_size == 50

    def test_event_bus_subcontract_json_serialization(self):
        """Test event bus subcontract JSON serialization."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        json_data = subcontract.model_dump_json()
        assert isinstance(json_data, str)
        assert "event_bus_type" in json_data
        assert "max_queue_size" in json_data

    def test_event_bus_subcontract_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            event_bus_type="distributed",
            max_queue_size=20000,
            batch_size=300,
            enable_event_retry=True,
            max_retry_attempts=5,
        )
        data = original.model_dump()
        restored = ModelEventBusSubcontract.model_validate(data)
        assert restored.event_bus_type == original.event_bus_type
        assert restored.max_queue_size == original.max_queue_size
        assert restored.batch_size == original.batch_size
        assert restored.enable_event_retry == original.enable_event_retry
        assert restored.max_retry_attempts == original.max_retry_attempts


@pytest.mark.unit
class TestModelEventBusSubcontractDefaultValues:
    """Test ModelEventBusSubcontract default values."""

    def test_event_logging_defaults(self):
        """Test event logging default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_event_logging is True
        assert subcontract.log_event_payloads is False

    def test_correlation_defaults(self):
        """Test correlation tracking default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.correlation_tracking is True
        assert subcontract.correlation_id_propagation is True

    def test_queue_management_defaults(self):
        """Test queue management default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.max_queue_size == 10000
        assert subcontract.queue_overflow_strategy == "block"

    def test_batch_processing_defaults(self):
        """Test batch processing default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.batch_size == 100
        assert subcontract.batch_timeout_ms == 5000

    def test_lifecycle_events_defaults(self):
        """Test lifecycle events default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_lifecycle_events is True
        assert subcontract.enable_introspection_events is True

    def test_retry_configuration_defaults(self):
        """Test retry configuration default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_event_retry is True
        assert subcontract.max_retry_attempts == 3
        assert subcontract.retry_delay_ms == 1000

    def test_validation_defaults(self):
        """Test event validation default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_event_validation is True
        assert subcontract.fail_fast_on_validation_errors is True

    def test_caching_defaults(self):
        """Test event caching default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_event_caching is True
        assert subcontract.cache_max_size == 100

    def test_monitoring_defaults(self):
        """Test monitoring default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.metrics_enabled is True
        assert subcontract.detailed_metrics is False
        assert subcontract.performance_monitoring is True

    def test_event_patterns_defaults(self):
        """Test event patterns default values."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.use_contract_event_patterns is True
        assert subcontract.fallback_to_node_name_patterns is True
        assert subcontract.default_event_patterns == [
            "*.discovery.*",
            "core.discovery.introspection_request",
        ]


@pytest.mark.unit
class TestModelEventBusSubcontractEdgeCases:
    """Test event bus subcontract edge cases."""

    def test_minimal_queue_size(self):
        """Test minimal queue size is accepted."""
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, max_queue_size=100
        )
        assert subcontract.max_queue_size == 100

    def test_minimal_batch_size(self):
        """Test minimal batch size is accepted."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION, batch_size=1)
        assert subcontract.batch_size == 1

    def test_all_features_disabled(self):
        """Test creating subcontract with all features disabled."""
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            event_bus_enabled=False,
            enable_event_logging=False,
            correlation_tracking=False,
            enable_lifecycle_events=False,
            enable_introspection_events=False,
            enable_event_retry=False,
            enable_event_validation=False,
            enable_event_caching=False,
            metrics_enabled=False,
            performance_monitoring=False,
        )
        assert subcontract.event_bus_enabled is False
        assert subcontract.enable_event_logging is False
        assert subcontract.correlation_tracking is False
        assert subcontract.enable_lifecycle_events is False

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per ConfigDict."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "event_bus_type": "memory",
            "extra_unknown_field": "should_be_ignored",
        }
        subcontract = ModelEventBusSubcontract.model_validate(data)
        assert subcontract.event_bus_type == "memory"
        assert not hasattr(subcontract, "extra_unknown_field")

    def test_empty_default_event_patterns(self):
        """Test creating subcontract with empty event patterns."""
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, default_event_patterns=[]
        )
        assert subcontract.default_event_patterns == []

    def test_custom_event_patterns(self):
        """Test creating subcontract with custom event patterns."""
        custom_patterns = ["app.events.*", "system.notifications.*"]
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, default_event_patterns=custom_patterns
        )
        assert subcontract.default_event_patterns == custom_patterns


@pytest.mark.unit
class TestModelEventBusSubcontractAttributes:
    """Test event bus subcontract attributes and metadata."""

    def test_event_bus_subcontract_attributes(self):
        """Test that event bus subcontract has expected attributes."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert hasattr(subcontract, "model_dump")
        assert callable(subcontract.model_dump)
        assert hasattr(ModelEventBusSubcontract, "model_validate")
        assert callable(ModelEventBusSubcontract.model_validate)

    def test_event_bus_subcontract_docstring(self):
        """Test event bus subcontract docstring."""
        assert ModelEventBusSubcontract.__doc__ is not None
        assert "event bus" in ModelEventBusSubcontract.__doc__.lower()

    def test_event_bus_subcontract_class_name(self):
        """Test event bus subcontract class name."""
        assert ModelEventBusSubcontract.__name__ == "ModelEventBusSubcontract"

    def test_event_bus_subcontract_module(self):
        """Test event bus subcontract module."""
        assert (
            ModelEventBusSubcontract.__module__
            == "omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract"
        )

    def test_event_bus_subcontract_copy(self):
        """Test event bus subcontract copying."""
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, event_bus_type="distributed"
        )
        copied = subcontract.model_copy()
        assert copied is not None
        assert copied.event_bus_type == "distributed"
        assert copied is not subcontract

    def test_event_bus_subcontract_equality(self):
        """Test event bus subcontract equality."""
        subcontract1 = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, event_bus_type="memory"
        )
        subcontract2 = ModelEventBusSubcontract(
            version=DEFAULT_VERSION, event_bus_type="memory"
        )
        assert subcontract1 == subcontract2

    def test_event_bus_subcontract_str_repr(self):
        """Test event bus subcontract string representations."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        str_repr = str(subcontract)
        assert isinstance(str_repr, str)

        repr_str = repr(subcontract)
        assert isinstance(repr_str, str)
        assert "ModelEventBusSubcontract" in repr_str

    def test_interface_version_format(self):
        """Test INTERFACE_VERSION format and accessibility."""
        version = ModelEventBusSubcontract.INTERFACE_VERSION
        assert isinstance(version, ModelSemVer)
        assert str(version) == "1.0.0"
        assert version.major >= 1


@pytest.mark.unit
class TestModelEventBusSubcontractConfigDict:
    """Test ModelEventBusSubcontract ConfigDict settings."""

    def test_extra_fields_are_ignored(self):
        """Test that extra='ignore' allows extra fields."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "event_bus_type": "memory",
            "unknown_field_1": "value1",
            "unknown_field_2": "value2",
        }
        subcontract = ModelEventBusSubcontract.model_validate(data)
        assert subcontract.event_bus_type == "memory"

    def test_validate_assignment_enabled(self):
        """Test that validate_assignment=True validates on assignment."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        # This should validate the new value
        subcontract.event_bus_type = "memory"
        assert subcontract.event_bus_type == "memory"

        # This should raise validation error
        with pytest.raises(ModelOnexError):
            subcontract.event_bus_type = "invalid_type"
