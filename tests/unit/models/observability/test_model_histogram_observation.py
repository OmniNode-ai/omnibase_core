"""Unit tests for ModelHistogramObservation."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.observability.model_histogram_observation import (
    ModelHistogramObservation,
)


class TestModelHistogramObservation:
    """Tests for ModelHistogramObservation model."""

    def test_create_basic(self) -> None:
        """Test creating histogram observation with required fields."""
        obs = ModelHistogramObservation(name="request_duration_seconds", value=0.123)
        assert obs.name == "request_duration_seconds"
        assert obs.labels == {}
        assert obs.value == 0.123

    def test_create_with_labels(self) -> None:
        """Test creating histogram observation with labels."""
        obs = ModelHistogramObservation(
            name="response_size_bytes",
            labels={"endpoint": "/api/users", "method": "GET"},
            value=1024.0,
        )
        assert obs.name == "response_size_bytes"
        assert obs.labels == {"endpoint": "/api/users", "method": "GET"}
        assert obs.value == 1024.0

    def test_value_must_be_non_negative(self) -> None:
        """Test that histogram value must be non-negative."""
        # Zero is allowed
        obs = ModelHistogramObservation(name="test", value=0.0)
        assert obs.value == 0.0

        # Negative is not allowed
        with pytest.raises(ValidationError) as exc_info:
            ModelHistogramObservation(name="test", value=-0.001)
        assert "greater_than_equal" in str(exc_info.value)

    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHistogramObservation(value=1.0)  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    def test_name_at_minimum_length(self) -> None:
        """Test name at minimum length (1 char) is valid."""
        obs = ModelHistogramObservation(name="x", value=1.0)
        assert obs.name == "x"

    def test_name_at_maximum_length(self) -> None:
        """Test name at maximum length (256 chars) is valid."""
        obs = ModelHistogramObservation(name="x" * 256, value=1.0)
        assert len(obs.name) == 256

    def test_empty_name_rejected(self) -> None:
        """Test empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHistogramObservation(name="", value=1.0)
        assert "string_too_short" in str(exc_info.value)

    def test_name_too_long_rejected(self) -> None:
        """Test name exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHistogramObservation(name="x" * 257, value=1.0)
        assert "string_too_long" in str(exc_info.value)

    def test_value_required(self) -> None:
        """Test that value is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHistogramObservation(name="test")  # type: ignore[call-arg]
        assert "value" in str(exc_info.value)

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        obs = ModelHistogramObservation(name="test", value=1.0)
        with pytest.raises(ValidationError):
            obs.value = 2.0  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHistogramObservation(name="test", value=1.0, extra="x")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()
