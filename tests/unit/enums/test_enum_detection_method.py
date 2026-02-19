# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumDetectionMethod enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_detection_method import EnumDetectionMethod


@pytest.mark.unit
class TestEnumDetectionMethod:
    """Test cases for EnumDetectionMethod enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumDetectionMethod.REGEX == "regex"
        assert EnumDetectionMethod.ML_MODEL == "ml_model"
        assert EnumDetectionMethod.ENTROPY_ANALYSIS == "entropy_analysis"
        assert EnumDetectionMethod.DICTIONARY_MATCH == "dictionary_match"
        assert EnumDetectionMethod.CONTEXT_ANALYSIS == "context_analysis"
        assert EnumDetectionMethod.HYBRID == "hybrid"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDetectionMethod, str)
        assert issubclass(EnumDetectionMethod, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        method = EnumDetectionMethod.REGEX
        assert isinstance(method, str)
        assert method == "regex"
        assert len(method) == 5
        assert method.startswith("reg")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDetectionMethod)
        assert len(values) == 6
        assert EnumDetectionMethod.REGEX in values
        assert EnumDetectionMethod.HYBRID in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "regex" in EnumDetectionMethod
        assert "invalid_method" not in EnumDetectionMethod

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        method1 = EnumDetectionMethod.REGEX
        method2 = EnumDetectionMethod.ML_MODEL

        assert method1 != method2
        assert method1 == "regex"
        assert method2 == "ml_model"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        method = EnumDetectionMethod.ENTROPY_ANALYSIS
        serialized = method.value
        assert serialized == "entropy_analysis"

        # Test JSON serialization
        import json

        json_str = json.dumps(method)
        assert json_str == '"entropy_analysis"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        method = EnumDetectionMethod("dictionary_match")
        assert method == EnumDetectionMethod.DICTIONARY_MATCH

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDetectionMethod("invalid_method")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "regex",
            "ml_model",
            "entropy_analysis",
            "dictionary_match",
            "context_analysis",
            "hybrid",
        }

        actual_values = {member.value for member in EnumDetectionMethod}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Methods used for detection" in EnumDetectionMethod.__doc__

    def test_enum_detection_methods(self):
        """Test that enum covers typical detection methods."""
        # Test pattern-based methods
        assert EnumDetectionMethod.REGEX in EnumDetectionMethod
        assert EnumDetectionMethod.DICTIONARY_MATCH in EnumDetectionMethod

        # Test ML-based methods
        assert EnumDetectionMethod.ML_MODEL in EnumDetectionMethod

        # Test analysis methods
        assert EnumDetectionMethod.ENTROPY_ANALYSIS in EnumDetectionMethod
        assert EnumDetectionMethod.CONTEXT_ANALYSIS in EnumDetectionMethod

        # Test hybrid method
        assert EnumDetectionMethod.HYBRID in EnumDetectionMethod
