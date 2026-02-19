# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelGaugeEmission."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.observability.model_gauge_emission import ModelGaugeEmission


class TestModelGaugeEmission:
    """Tests for ModelGaugeEmission model."""

    def test_create_basic(self) -> None:
        """Test creating gauge with required fields."""
        gauge = ModelGaugeEmission(name="queue_depth", value=42.0)
        assert gauge.name == "queue_depth"
        assert gauge.labels == {}
        assert gauge.value == 42.0

    def test_create_with_labels(self) -> None:
        """Test creating gauge with labels."""
        gauge = ModelGaugeEmission(
            name="temperature_celsius",
            labels={"sensor": "cpu", "location": "rack1"},
            value=-10.5,
        )
        assert gauge.name == "temperature_celsius"
        assert gauge.labels == {"sensor": "cpu", "location": "rack1"}
        assert gauge.value == -10.5

    def test_value_can_be_negative(self) -> None:
        """Test that gauge value can be negative."""
        gauge = ModelGaugeEmission(name="balance", value=-100.0)
        assert gauge.value == -100.0

    def test_value_can_be_zero(self) -> None:
        """Test that gauge value can be zero."""
        gauge = ModelGaugeEmission(name="active_connections", value=0.0)
        assert gauge.value == 0.0

    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGaugeEmission(value=1.0)  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    def test_name_at_minimum_length(self) -> None:
        """Test name at minimum length (1 char) is valid."""
        gauge = ModelGaugeEmission(name="x", value=1.0)
        assert gauge.name == "x"

    def test_name_at_maximum_length(self) -> None:
        """Test name at maximum length (256 chars) is valid."""
        gauge = ModelGaugeEmission(name="x" * 256, value=1.0)
        assert len(gauge.name) == 256

    def test_empty_name_rejected(self) -> None:
        """Test empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGaugeEmission(name="", value=1.0)
        assert "string_too_short" in str(exc_info.value)

    def test_name_too_long_rejected(self) -> None:
        """Test name exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGaugeEmission(name="x" * 257, value=1.0)
        assert "string_too_long" in str(exc_info.value)

    def test_value_required(self) -> None:
        """Test that value is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGaugeEmission(name="test")  # type: ignore[call-arg]
        assert "value" in str(exc_info.value)

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        gauge = ModelGaugeEmission(name="test", value=1.0)
        with pytest.raises(ValidationError):
            gauge.value = 2.0  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGaugeEmission(name="test", value=1.0, unknown="x")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()
