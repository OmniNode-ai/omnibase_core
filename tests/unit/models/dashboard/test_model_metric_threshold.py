# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelMetricThreshold."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard import ModelMetricThreshold


@pytest.mark.unit
class TestModelMetricThreshold:
    """Tests for ModelMetricThreshold model (OMN-16948: color names a theme token)."""

    @pytest.mark.parametrize(
        "token",
        ["color_status_success", "color_status_warning", "color_status_error"],
    )
    def test_theme_token_name_is_accepted(self, token: str) -> None:
        """A colour token of ModelRendererThemeContract is a valid threshold colour."""
        threshold = ModelMetricThreshold(value=90.0, color=token)
        assert threshold.color == token

    def test_create_with_label(self) -> None:
        """Test creating threshold with label."""
        threshold = ModelMetricThreshold(
            value=50.0, color="color_status_warning", label="Warning"
        )
        assert threshold.color == "color_status_warning"
        assert threshold.label == "Warning"

    @pytest.mark.parametrize(
        "value",
        [
            "#FF0000",
            "#F00",
            "#FF0000FF",
            "FF0000",
            "rgb(255, 0, 0)",
            "",
            "#",
            "spacing_md",
            "color_not_a_token",
        ],
    )
    def test_colour_values_and_non_colour_tokens_are_rejected(self, value: str) -> None:
        """A colour value, a non-colour token or an unknown name is refused."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricThreshold(value=90.0, color=value)
        errors = exc_info.value.errors()
        assert any(
            e["type"] == "value_error" and e["loc"] == ("color",) for e in errors
        )

    def test_roundtrip_serialization(self) -> None:
        """Test model_dump and model_validate roundtrip."""
        threshold = ModelMetricThreshold(
            value=95.0, color="color_status_error", label="Critical"
        )
        data = threshold.model_dump()
        restored = ModelMetricThreshold.model_validate(data)
        assert restored == threshold

    def test_frozen_model(self) -> None:
        """Test that model is frozen."""
        threshold = ModelMetricThreshold(value=50.0, color="color_status_info")
        with pytest.raises((ValidationError, TypeError)):
            threshold.value = 100.0  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelMetricThreshold(
                value=50.0,
                color="color_status_info",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )
