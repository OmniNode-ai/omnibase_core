# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelMetricThreshold."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard import ModelMetricThreshold


@pytest.mark.unit
class TestModelMetricThreshold:
    """Tests for ModelMetricThreshold model."""

    def test_create_with_valid_hex_6(self) -> None:
        """Test creating threshold with valid 6-digit hex color."""
        threshold = ModelMetricThreshold(value=90.0, color="#FF0000")
        assert threshold.value == 90.0
        assert threshold.color == "#FF0000"
        assert threshold.label is None

    def test_create_with_valid_hex_3(self) -> None:
        """Test creating threshold with valid 3-digit hex color."""
        threshold = ModelMetricThreshold(value=50.0, color="#F00", label="Warning")
        assert threshold.color == "#F00"
        assert threshold.label == "Warning"

    def test_create_with_valid_hex_8_rgba(self) -> None:
        """Test creating threshold with valid 8-digit hex color (RRGGBBAA)."""
        threshold = ModelMetricThreshold(value=75.0, color="#FF0000FF")
        assert threshold.color == "#FF0000FF"

    def test_create_with_valid_hex_4_rgba(self) -> None:
        """Test creating threshold with valid 4-digit hex color (RGBA)."""
        threshold = ModelMetricThreshold(value=25.0, color="#F00F")
        assert threshold.color == "#F00F"

    def test_lowercase_hex_valid(self) -> None:
        """Test that lowercase hex is valid."""
        threshold = ModelMetricThreshold(value=80.0, color="#abcdef")
        assert threshold.color == "#abcdef"

    def test_mixed_case_hex_valid(self) -> None:
        """Test that mixed case hex is valid."""
        threshold = ModelMetricThreshold(value=80.0, color="#AbCdEf")
        assert threshold.color == "#AbCdEf"

    def test_invalid_hex_missing_hash(self) -> None:
        """Test that hex without # is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color="FF0000")
        assert "Invalid hex color format" in str(exc_info.value)

    def test_invalid_hex_wrong_length(self) -> None:
        """Test that hex with wrong length is invalid."""
        # 5 chars is invalid (not 3, 4, 6, or 8)
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color="#FF000")
        assert "Invalid hex color format" in str(exc_info.value)

        # 7 chars is also invalid
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color="#FF0000F")
        assert "Invalid hex color format" in str(exc_info.value)

    def test_invalid_hex_non_hex_chars(self) -> None:
        """Test that non-hex characters are invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color="#GGGGGG")
        assert "Invalid hex color format" in str(exc_info.value)

    def test_invalid_hex_empty(self) -> None:
        """Test that empty color is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color="")
        assert "Invalid hex color format" in str(exc_info.value)

    def test_invalid_hex_only_hash(self) -> None:
        """Test that only # is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color="#")
        assert "Invalid hex color format" in str(exc_info.value)

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
