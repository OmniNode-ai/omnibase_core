# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelMetricThreshold."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard import ModelMetricThreshold


@pytest.mark.unit
class TestModelMetricThreshold:
    """Tests for ModelMetricThreshold model."""

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("#FF0000", "6-digit hex"),
            ("#F00", "3-digit hex"),
            ("#FF0000FF", "8-digit hex (RRGGBBAA)"),
            ("#F00F", "4-digit hex (RGBA)"),
            ("#abcdef", "lowercase hex"),
            ("#AbCdEf", "mixed case hex"),
        ],
    )
    def test_valid_hex_color_formats(self, color: str, description: str) -> None:
        """Test creating threshold with valid hex color formats."""
        threshold = ModelMetricThreshold(value=90.0, color=color)
        assert threshold.color == color

    def test_create_with_label(self) -> None:
        """Test creating threshold with label."""
        threshold = ModelMetricThreshold(value=50.0, color="#F00", label="Warning")
        assert threshold.color == "#F00"
        assert threshold.label == "Warning"

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("FF0000", "missing hash prefix"),
            ("#FF000", "5 chars (invalid length)"),
            ("#FF0000F", "7 chars (invalid length)"),
            ("#GGGGGG", "non-hex characters"),
            ("", "empty string"),
            ("#", "only hash"),
        ],
    )
    def test_invalid_hex_color_formats(self, color: str, description: str) -> None:
        """Test that invalid hex color formats raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color=color)
        # Check for value_error type which is raised by our custom hex color validator
        errors = exc_info.value.errors()
        assert any(
            e["type"] == "value_error" and e["loc"] == ("color",) for e in errors
        )

    def test_roundtrip_serialization(self) -> None:
        """Test model_dump and model_validate roundtrip."""
        threshold = ModelMetricThreshold(value=95.0, color="#00FF00", label="Critical")
        data = threshold.model_dump()
        restored = ModelMetricThreshold.model_validate(data)
        assert restored == threshold

    def test_frozen_model(self) -> None:
        """Test that model is frozen."""
        threshold = ModelMetricThreshold(value=50.0, color="#000000")
        with pytest.raises((ValidationError, TypeError)):
            threshold.value = 100.0  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelMetricThreshold(
                value=50.0,
                color="#000000",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )
