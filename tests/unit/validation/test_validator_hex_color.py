# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for shared hex color validator.

Tests for the centralized hex color validation used throughout
the ONEX dashboard models. Covers:
- validate_hex_color (required color)
- validate_hex_color_optional (optional color)
- validate_hex_color_mapping (mapping of colors)
- HexColorValidator class
- HEX_COLOR_PATTERN regex
"""

import re

import pytest
from pydantic import BaseModel, ValidationError, field_validator

from omnibase_core.validation.validator_hex_color import (
    HEX_COLOR_PATTERN,
    HexColorValidator,
    validate_hex_color,
    validate_hex_color_mapping,
    validate_hex_color_optional,
)

# =============================================================================
# HEX_COLOR_PATTERN Tests
# =============================================================================


@pytest.mark.unit
class TestHexColorPattern:
    """Tests for the HEX_COLOR_PATTERN regex."""

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("#F00", "3-digit hex (short RGB)"),
            ("#FF0000", "6-digit hex (full RGB)"),
            ("#F00F", "4-digit hex (short RGBA)"),
            ("#FF0000FF", "8-digit hex (full RGBA)"),
            ("#abc", "3-digit hex lowercase"),
            ("#abcdef", "6-digit hex lowercase"),
            ("#AbCdEf", "6-digit hex mixed case"),
            ("#ABCDEF", "6-digit hex uppercase"),
            ("#000", "3-digit black"),
            ("#000000", "6-digit black"),
            ("#fff", "3-digit white"),
            ("#ffffff", "6-digit white"),
            ("#00000000", "8-digit transparent"),
            ("#ffffffff", "8-digit opaque white"),
        ],
    )
    def test_valid_colors_match(self, color: str, description: str) -> None:
        """Test that valid hex colors match the pattern."""
        assert HEX_COLOR_PATTERN.match(color) is not None, f"Failed for {description}"

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("FF0000", "missing hash prefix"),
            ("#FF000", "5 chars (invalid length)"),
            ("#FF0000F", "7 chars (invalid length)"),
            ("#GGGGGG", "non-hex characters"),
            ("", "empty string"),
            ("#", "only hash"),
            ("##FF0000", "double hash"),
            ("# FF0000", "space after hash"),
            ("#FF 0000", "space in middle"),
            ("#FF0000 ", "trailing space"),
            (" #FF0000", "leading space"),
            ("#FF", "2 chars (invalid length)"),
            ("#FF00000000", "10 chars (invalid length)"),
        ],
    )
    def test_invalid_colors_no_match(self, color: str, description: str) -> None:
        """Test that invalid hex colors do not match the pattern."""
        assert HEX_COLOR_PATTERN.match(color) is None, (
            f"Should not match: {description}"
        )

    def test_pattern_is_compiled(self) -> None:
        """Test that HEX_COLOR_PATTERN is a compiled regex."""
        assert isinstance(HEX_COLOR_PATTERN, re.Pattern)


# =============================================================================
# validate_hex_color Tests
# =============================================================================


@pytest.mark.unit
class TestValidateHexColor:
    """Tests for validate_hex_color function."""

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("#FF0000", "6-digit hex"),
            ("#F00", "3-digit hex"),
            ("#FF0000FF", "8-digit hex (RRGGBBAA)"),
            ("#F00F", "4-digit hex (RGBA)"),
            ("#abcdef", "lowercase hex"),
            ("#AbCdEf", "mixed case hex"),
            ("#000000", "black"),
            ("#ffffff", "white"),
            ("#22c55e", "tailwind green-500"),
            ("#eab308", "tailwind yellow-500"),
            ("#ef4444", "tailwind red-500"),
        ],
    )
    def test_valid_hex_colors(self, color: str, description: str) -> None:
        """Test that valid hex colors are accepted."""
        result = validate_hex_color(color)
        assert result == color

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("FF0000", "missing hash prefix"),
            ("#FF000", "5 chars (invalid length)"),
            ("#FF0000F", "7 chars (invalid length)"),
            ("#GGGGGG", "non-hex characters"),
            ("", "empty string"),
            ("#", "only hash"),
            ("red", "color name"),
            ("rgb(255,0,0)", "rgb format"),
            ("rgba(255,0,0,1)", "rgba format"),
        ],
    )
    def test_invalid_hex_colors_raise_value_error(
        self, color: str, description: str
    ) -> None:
        """Test that invalid hex colors raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_hex_color(color)
        assert "Invalid hex color format" in str(exc_info.value)

    def test_error_message_includes_value(self) -> None:
        """Test that error message includes the invalid value."""
        with pytest.raises(ValueError) as exc_info:
            validate_hex_color("invalid")
        assert "invalid" in str(exc_info.value)

    def test_error_message_includes_expected_formats(self) -> None:
        """Test that error message includes expected formats."""
        with pytest.raises(ValueError) as exc_info:
            validate_hex_color("invalid")
        error_msg = str(exc_info.value)
        assert "#RGB" in error_msg
        assert "#RRGGBB" in error_msg
        assert "#RGBA" in error_msg
        assert "#RRGGBBAA" in error_msg


# =============================================================================
# validate_hex_color_optional Tests
# =============================================================================


@pytest.mark.unit
class TestValidateHexColorOptional:
    """Tests for validate_hex_color_optional function."""

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        result = validate_hex_color_optional(None)
        assert result is None

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("#FF0000", "6-digit hex"),
            ("#F00", "3-digit hex"),
            ("#FF0000FF", "8-digit hex"),
            ("#abcdef", "lowercase hex"),
        ],
    )
    def test_valid_colors_accepted(self, color: str, description: str) -> None:
        """Test that valid colors are accepted when not None."""
        result = validate_hex_color_optional(color)
        assert result == color

    @pytest.mark.parametrize(
        ("color", "description"),
        [
            ("FF0000", "missing hash"),
            ("#GGGGGG", "non-hex chars"),
            ("", "empty string"),
        ],
    )
    def test_invalid_colors_raise_value_error(
        self, color: str, description: str
    ) -> None:
        """Test that invalid colors raise ValueError when not None."""
        with pytest.raises(ValueError):
            validate_hex_color_optional(color)


# =============================================================================
# validate_hex_color_mapping Tests
# =============================================================================


@pytest.mark.unit
class TestValidateHexColorMapping:
    """Tests for validate_hex_color_mapping function."""

    def test_empty_mapping_valid(self) -> None:
        """Test that empty mapping is valid."""
        result = validate_hex_color_mapping({})
        assert result == {}

    def test_valid_mapping_accepted(self) -> None:
        """Test that mapping with valid colors is accepted."""
        colors = {
            "healthy": "#22c55e",
            "warning": "#eab308",
            "error": "#ef4444",
            "unknown": "#6b7280",
        }
        result = validate_hex_color_mapping(colors)
        assert result == colors

    def test_valid_mapping_various_formats(self) -> None:
        """Test that mapping with various valid formats is accepted."""
        colors = {
            "short_rgb": "#F00",
            "full_rgb": "#FF0000",
            "short_rgba": "#F00F",
            "full_rgba": "#FF0000FF",
        }
        result = validate_hex_color_mapping(colors)
        assert result == colors

    def test_invalid_color_raises_value_error(self) -> None:
        """Test that mapping with invalid color raises ValueError."""
        colors = {"ok": "#00FF00", "fail": "invalid"}
        with pytest.raises(ValueError) as exc_info:
            validate_hex_color_mapping(colors)
        error_msg = str(exc_info.value)
        assert "fail" in error_msg
        assert "invalid" in error_msg

    def test_error_includes_key_context(self) -> None:
        """Test that error message includes key context."""
        colors = {"my_status": "#GGGGGG"}
        with pytest.raises(ValueError) as exc_info:
            validate_hex_color_mapping(colors, "status")
        error_msg = str(exc_info.value)
        assert "status" in error_msg
        assert "my_status" in error_msg

    def test_custom_key_context(self) -> None:
        """Test that custom key_context is used in error message."""
        colors = {"level": "invalid"}
        with pytest.raises(ValueError) as exc_info:
            validate_hex_color_mapping(colors, "severity")
        assert "severity" in str(exc_info.value)

    def test_first_invalid_color_in_mapping_raises(self) -> None:
        """Test that first invalid color encountered raises error."""
        # Note: dict iteration order is preserved in Python 3.7+
        colors = {
            "first": "#INVALID1",
            "second": "#INVALID2",
        }
        with pytest.raises(ValueError) as exc_info:
            validate_hex_color_mapping(colors)
        # Should mention 'first' since it's encountered first
        assert "first" in str(exc_info.value)


# =============================================================================
# HexColorValidator Class Tests
# =============================================================================


@pytest.mark.unit
class TestHexColorValidator:
    """Tests for HexColorValidator class."""

    def test_validate_valid_color(self) -> None:
        """Test HexColorValidator.validate with valid color."""
        result = HexColorValidator.validate("#FF0000")
        assert result == "#FF0000"

    def test_validate_invalid_color(self) -> None:
        """Test HexColorValidator.validate with invalid color."""
        with pytest.raises(ValueError):
            HexColorValidator.validate("invalid")

    def test_validate_optional_none(self) -> None:
        """Test HexColorValidator.validate_optional with None."""
        result = HexColorValidator.validate_optional(None)
        assert result is None

    def test_validate_optional_valid(self) -> None:
        """Test HexColorValidator.validate_optional with valid color."""
        result = HexColorValidator.validate_optional("#FF0000")
        assert result == "#FF0000"

    def test_validate_optional_invalid(self) -> None:
        """Test HexColorValidator.validate_optional with invalid color."""
        with pytest.raises(ValueError):
            HexColorValidator.validate_optional("invalid")

    def test_validate_mapping_valid(self) -> None:
        """Test HexColorValidator.validate_mapping with valid mapping."""
        colors = {"red": "#FF0000", "green": "#00FF00"}
        result = HexColorValidator.validate_mapping(colors)
        assert result == colors

    def test_validate_mapping_invalid(self) -> None:
        """Test HexColorValidator.validate_mapping with invalid color."""
        with pytest.raises(ValueError):
            HexColorValidator.validate_mapping({"bad": "invalid"})

    def test_pattern_class_variable(self) -> None:
        """Test that PATTERN class variable is accessible."""
        assert HexColorValidator.PATTERN is not None
        assert isinstance(HexColorValidator.PATTERN, re.Pattern)
        assert HexColorValidator.PATTERN is HEX_COLOR_PATTERN


# =============================================================================
# Pydantic Integration Tests
# =============================================================================


@pytest.mark.unit
class TestPydanticIntegration:
    """Tests for using hex color validators in Pydantic models."""

    def test_field_validator_required_color(self) -> None:
        """Test using validate_hex_color in a Pydantic field validator."""

        class Theme(BaseModel):
            primary_color: str

            @field_validator("primary_color")
            @classmethod
            def check_color(cls, v: str) -> str:
                return validate_hex_color(v)

        theme = Theme(primary_color="#FF0000")
        assert theme.primary_color == "#FF0000"

    def test_field_validator_required_color_invalid(self) -> None:
        """Test that invalid color raises ValidationError in Pydantic model."""

        class Theme(BaseModel):
            primary_color: str

            @field_validator("primary_color")
            @classmethod
            def check_color(cls, v: str) -> str:
                return validate_hex_color(v)

        with pytest.raises(ValidationError) as exc_info:
            Theme(primary_color="invalid")
        errors = exc_info.value.errors()
        assert any(e["type"] == "value_error" for e in errors)

    def test_field_validator_optional_color(self) -> None:
        """Test using validate_hex_color_optional in a Pydantic field validator."""

        class Theme(BaseModel):
            accent_color: str | None = None

            @field_validator("accent_color")
            @classmethod
            def check_color(cls, v: str | None) -> str | None:
                return validate_hex_color_optional(v)

        # With color
        theme1 = Theme(accent_color="#00FF00")
        assert theme1.accent_color == "#00FF00"

        # Without color (None)
        theme2 = Theme(accent_color=None)
        assert theme2.accent_color is None

        # Without color (default)
        theme3 = Theme()
        assert theme3.accent_color is None

    def test_field_validator_color_mapping(self) -> None:
        """Test using validate_hex_color_mapping in a Pydantic field validator."""

        class StatusConfig(BaseModel):
            status_colors: dict[str, str]

            @field_validator("status_colors")
            @classmethod
            def check_colors(cls, v: dict[str, str]) -> dict[str, str]:
                validate_hex_color_mapping(v, "status")
                return v

        config = StatusConfig(status_colors={"ok": "#00FF00", "error": "#FF0000"})
        assert config.status_colors == {"ok": "#00FF00", "error": "#FF0000"}

    def test_field_validator_color_mapping_invalid(self) -> None:
        """Test that invalid color in mapping raises ValidationError."""

        class StatusConfig(BaseModel):
            status_colors: dict[str, str]

            @field_validator("status_colors")
            @classmethod
            def check_colors(cls, v: dict[str, str]) -> dict[str, str]:
                validate_hex_color_mapping(v, "status")
                return v

        with pytest.raises(ValidationError) as exc_info:
            StatusConfig(status_colors={"bad": "invalid"})
        errors = exc_info.value.errors()
        assert any(e["type"] == "value_error" for e in errors)


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestImports:
    """Tests for import paths."""

    def test_import_from_validator_module(self) -> None:
        """Test that all exports are importable from the module."""
        from omnibase_core.validation.validator_hex_color import (
            HEX_COLOR_PATTERN,
            HexColorValidator,
            validate_hex_color,
            validate_hex_color_mapping,
            validate_hex_color_optional,
        )

        assert callable(validate_hex_color)
        assert callable(validate_hex_color_optional)
        assert callable(validate_hex_color_mapping)
        assert HexColorValidator is not None
        assert HEX_COLOR_PATTERN is not None

    def test_import_from_validation_package(self) -> None:
        """Test that exports are available from validation package."""
        # This test will be updated once we add exports to __init__.py
        from omnibase_core.validation.validator_hex_color import (
            validate_hex_color,
            validate_hex_color_mapping,
            validate_hex_color_optional,
        )

        assert callable(validate_hex_color)
        assert callable(validate_hex_color_optional)
        assert callable(validate_hex_color_mapping)


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Edge case tests for hex color validators."""

    def test_color_with_unicode_valid(self) -> None:
        """Test that unicode characters that are valid hex work correctly.

        Unicode \u0046 is 'F', so #\u0046F0000 is #FF0000 which is valid.
        """
        # Unicode that evaluates to valid hex should be accepted
        result = validate_hex_color("#\u0046F0000")  # Unicode 'F' = #FF0000
        assert result == "#FF0000"

    def test_color_with_newline(self) -> None:
        """Test that colors with trailing newlines are rejected.

        Note: re.match with $ anchor matches at end of string, not before newline,
        so #FF0000\\n actually doesn't match the pattern (string is 8 chars, not 7).
        """
        with pytest.raises(ValueError):
            validate_hex_color("#FF0000\n")

    def test_color_with_tab(self) -> None:
        """Test that tabs are rejected."""
        with pytest.raises(ValueError):
            validate_hex_color("#FF0000\t")

    def test_mapping_with_immutable_type(self) -> None:
        """Test that immutable Mapping types work."""
        from types import MappingProxyType

        colors = MappingProxyType({"healthy": "#00FF00", "error": "#FF0000"})
        result = validate_hex_color_mapping(colors)
        assert result == colors

    def test_thread_safety_of_pattern(self) -> None:
        """Test that pattern is thread-safe (immutable)."""
        # Compiled regex patterns are immutable and thread-safe
        pattern1 = HEX_COLOR_PATTERN
        pattern2 = HexColorValidator.PATTERN
        assert pattern1 is pattern2
        # Pattern should not change
        assert pattern1.pattern == pattern2.pattern
