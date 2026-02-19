# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelPayloadMetric.

This module tests the ModelPayloadMetric model for metric recording intents, verifying:
1. Field validation (name, value, metric_type, labels, unit)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import ModelPayloadMetric


@pytest.mark.unit
class TestModelPayloadMetricInstantiation:
    """Test ModelPayloadMetric instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = ModelPayloadMetric(name="test.metric", value=42.0)
        assert payload.name == "test.metric"
        assert payload.value == 42.0
        assert payload.intent_type == "record_metric"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = ModelPayloadMetric(
            name="http.request.duration",
            value=0.125,
            metric_type="histogram",
            labels={"method": "GET", "path": "/api"},
            unit="seconds",
        )
        assert payload.name == "http.request.duration"
        assert payload.value == 0.125
        assert payload.metric_type == "histogram"
        assert payload.labels == {"method": "GET", "path": "/api"}
        assert payload.unit == "seconds"


@pytest.mark.unit
class TestModelPayloadMetricDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'record_metric'."""
        payload = ModelPayloadMetric(name="test.metric", value=1.0)
        assert payload.intent_type == "record_metric"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadMetric(name="test.metric", value=1.0)
        data = payload.model_dump()
        assert data["intent_type"] == "record_metric"


@pytest.mark.unit
class TestModelPayloadMetricNameValidation:
    """Test name field validation."""

    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(value=1.0)  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    def test_name_min_length(self) -> None:
        """Test name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(name="", value=1.0)
        assert "name" in str(exc_info.value)

    def test_name_max_length(self) -> None:
        """Test name maximum length validation."""
        long_name = "a" * 257
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(name=long_name, value=1.0)
        assert "name" in str(exc_info.value)

    def test_name_pattern_valid(self) -> None:
        """Test valid name patterns."""
        valid_names = [
            "metric",
            "http.request.count",
            "cache_hits",
            "db.query.duration_ms",
        ]
        for name in valid_names:
            payload = ModelPayloadMetric(name=name, value=1.0)
            assert payload.name == name

    def test_name_pattern_invalid_start_with_number(self) -> None:
        """Test that name cannot start with number."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(name="123metric", value=1.0)
        assert "name" in str(exc_info.value)

    def test_name_pattern_invalid_special_chars(self) -> None:
        """Test that name cannot contain special chars."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(name="metric-name", value=1.0)  # hyphen not allowed
        assert "name" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadMetricMetricTypeValidation:
    """Test metric_type field validation."""

    def test_valid_metric_type_counter(self) -> None:
        """Test valid counter metric type."""
        payload = ModelPayloadMetric(name="test", value=1.0, metric_type="counter")
        assert payload.metric_type == "counter"

    def test_valid_metric_type_gauge(self) -> None:
        """Test valid gauge metric type."""
        payload = ModelPayloadMetric(name="test", value=1.0, metric_type="gauge")
        assert payload.metric_type == "gauge"

    def test_valid_metric_type_histogram(self) -> None:
        """Test valid histogram metric type."""
        payload = ModelPayloadMetric(name="test", value=1.0, metric_type="histogram")
        assert payload.metric_type == "histogram"

    def test_valid_metric_type_summary(self) -> None:
        """Test valid summary metric type."""
        payload = ModelPayloadMetric(name="test", value=1.0, metric_type="summary")
        assert payload.metric_type == "summary"

    def test_invalid_metric_type_rejected(self) -> None:
        """Test that invalid metric type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(name="test", value=1.0, metric_type="invalid")  # type: ignore[arg-type]
        assert "metric_type" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadMetricDefaultValues:
    """Test default values."""

    def test_default_metric_type(self) -> None:
        """Test default metric_type is gauge."""
        payload = ModelPayloadMetric(name="test", value=1.0)
        assert payload.metric_type == "gauge"

    def test_default_labels(self) -> None:
        """Test default labels is empty dict."""
        payload = ModelPayloadMetric(name="test", value=1.0)
        assert payload.labels == {}

    def test_default_unit(self) -> None:
        """Test default unit is None."""
        payload = ModelPayloadMetric(name="test", value=1.0)
        assert payload.unit is None


@pytest.mark.unit
class TestModelPayloadMetricValueValidation:
    """Test value field validation."""

    def test_value_required(self) -> None:
        """Test that value is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(name="test")  # type: ignore[call-arg]
        assert "value" in str(exc_info.value)

    def test_value_accepts_integer(self) -> None:
        """Test that value accepts integer."""
        payload = ModelPayloadMetric(name="test", value=42)
        assert payload.value == 42.0

    def test_value_accepts_float(self) -> None:
        """Test that value accepts float."""
        payload = ModelPayloadMetric(name="test", value=3.14159)
        assert payload.value == 3.14159

    def test_value_accepts_negative(self) -> None:
        """Test that value accepts negative numbers."""
        payload = ModelPayloadMetric(name="test", value=-10.5)
        assert payload.value == -10.5

    def test_value_accepts_zero(self) -> None:
        """Test that value accepts zero."""
        payload = ModelPayloadMetric(name="test", value=0)
        assert payload.value == 0.0


@pytest.mark.unit
class TestModelPayloadMetricUnitValidation:
    """Test unit field validation."""

    def test_unit_max_length(self) -> None:
        """Test unit maximum length validation."""
        long_unit = "a" * 33
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(name="test", value=1.0, unit=long_unit)
        assert "unit" in str(exc_info.value)

    def test_valid_unit_values(self) -> None:
        """Test valid unit values."""
        valid_units = ["seconds", "bytes", "requests", "percent", "ms"]
        for unit in valid_units:
            payload = ModelPayloadMetric(name="test", value=1.0, unit=unit)
            assert payload.unit == unit


@pytest.mark.unit
class TestModelPayloadMetricImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_name(self) -> None:
        """Test that name cannot be modified after creation."""
        payload = ModelPayloadMetric(name="test", value=1.0)
        with pytest.raises(ValidationError):
            payload.name = "new_name"  # type: ignore[misc]

    def test_cannot_modify_value(self) -> None:
        """Test that value cannot be modified after creation."""
        payload = ModelPayloadMetric(name="test", value=1.0)
        with pytest.raises(ValidationError):
            payload.value = 2.0  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadMetricSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = ModelPayloadMetric(
            name="http.request.count",
            value=100.0,
            metric_type="counter",
            labels={"status": "200"},
            unit="requests",
        )
        data = original.model_dump()
        restored = ModelPayloadMetric.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadMetric(name="test", value=42.0)
        json_str = original.model_dump_json()
        restored = ModelPayloadMetric.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = ModelPayloadMetric(name="test", value=1.0)
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "name",
            "value",
            "metric_type",
            "labels",
            "unit",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestModelPayloadMetricExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadMetric(
                name="test",
                value=1.0,
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
