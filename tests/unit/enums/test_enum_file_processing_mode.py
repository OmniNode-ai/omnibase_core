# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumFileProcessingMode enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_file_processing_mode import EnumFileProcessingMode


@pytest.mark.unit
class TestEnumFileProcessingMode:
    """Test cases for EnumFileProcessingMode enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumFileProcessingMode.FAST.value == "FAST"
        assert EnumFileProcessingMode.STANDARD.value == "STANDARD"
        assert EnumFileProcessingMode.COMPREHENSIVE.value == "COMPREHENSIVE"

    def test_enum_inheritance(self):
        """Test that enum inherits from Enum."""
        assert issubclass(EnumFileProcessingMode, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumFileProcessingMode.FAST) == "EnumFileProcessingMode.FAST"
        assert str(EnumFileProcessingMode.STANDARD) == "EnumFileProcessingMode.STANDARD"
        assert (
            str(EnumFileProcessingMode.COMPREHENSIVE)
            == "EnumFileProcessingMode.COMPREHENSIVE"
        )

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumFileProcessingMode)
        assert len(values) == 3
        assert EnumFileProcessingMode.FAST in values
        assert EnumFileProcessingMode.STANDARD in values
        assert EnumFileProcessingMode.COMPREHENSIVE in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "FAST" in EnumFileProcessingMode._value2member_map_
        assert "STANDARD" in EnumFileProcessingMode._value2member_map_
        assert "COMPREHENSIVE" in EnumFileProcessingMode._value2member_map_
        assert "invalid" not in EnumFileProcessingMode._value2member_map_

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumFileProcessingMode.FAST.value == "FAST"
        assert EnumFileProcessingMode.STANDARD.value == "STANDARD"
        assert EnumFileProcessingMode.COMPREHENSIVE.value == "COMPREHENSIVE"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumFileProcessingMode.FAST.value == "FAST"
        assert EnumFileProcessingMode.STANDARD.value == "STANDARD"
        assert EnumFileProcessingMode.COMPREHENSIVE.value == "COMPREHENSIVE"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumFileProcessingMode("FAST") == EnumFileProcessingMode.FAST
        assert EnumFileProcessingMode("STANDARD") == EnumFileProcessingMode.STANDARD
        assert (
            EnumFileProcessingMode("COMPREHENSIVE")
            == EnumFileProcessingMode.COMPREHENSIVE
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumFileProcessingMode("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [
            mode.value for mode in EnumFileProcessingMode.__members__.values()
        ]
        expected_values = ["FAST", "STANDARD", "COMPREHENSIVE"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "File processing modes for stamp operations"
            in EnumFileProcessingMode.__doc__
        )
