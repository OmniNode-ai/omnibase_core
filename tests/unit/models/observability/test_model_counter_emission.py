"""Unit tests for ModelCounterEmission."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.observability.model_counter_emission import (
    ModelCounterEmission,
)


class TestModelCounterEmission:
    """Tests for ModelCounterEmission model."""

    def test_create_with_defaults(self) -> None:
        """Test creating counter with default increment."""
        counter = ModelCounterEmission(name="requests_total")
        assert counter.name == "requests_total"
        assert counter.labels == {}
        assert counter.increment == 1.0

    def test_create_with_labels(self) -> None:
        """Test creating counter with labels."""
        counter = ModelCounterEmission(
            name="http_requests_total",
            labels={"method": "GET", "status": "200"},
            increment=5.0,
        )
        assert counter.name == "http_requests_total"
        assert counter.labels == {"method": "GET", "status": "200"}
        assert counter.increment == 5.0

    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCounterEmission()  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    def test_name_min_length(self) -> None:
        """Test name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCounterEmission(name="")
        assert "string_too_short" in str(exc_info.value)

    def test_name_max_length(self) -> None:
        """Test name maximum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCounterEmission(name="x" * 257)
        assert "string_too_long" in str(exc_info.value)

    def test_increment_must_be_positive(self) -> None:
        """Test that increment must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCounterEmission(name="test", increment=0)
        assert "greater_than" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelCounterEmission(name="test", increment=-1)
        assert "greater_than" in str(exc_info.value)

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        counter = ModelCounterEmission(name="test")
        with pytest.raises(ValidationError):
            counter.name = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCounterEmission(name="test", extra_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()
