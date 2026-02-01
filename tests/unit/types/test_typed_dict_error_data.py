"""
Test suite for TypedDictErrorData.
"""

import pytest

from omnibase_core.types.typed_dict_error_data import TypedDictErrorData


@pytest.mark.unit
class TestTypedDictErrorData:
    """Test TypedDictErrorData functionality."""

    def test_typed_dict_error_data_empty(self):
        """Test creating empty TypedDictErrorData."""
        error_data: TypedDictErrorData = {}

        # All fields are optional, so empty dict should be valid
        assert isinstance(error_data, dict)

    def test_typed_dict_error_data_with_all_fields(self):
        """Test TypedDictErrorData with all fields."""
        error_data: TypedDictErrorData = {
            "error_level_count": 5,
            "warning_count": 3,
            "critical_error_count": 1,
        }

        assert error_data["error_level_count"] == 5
        assert error_data["warning_count"] == 3
        assert error_data["critical_error_count"] == 1

    def test_typed_dict_error_data_partial_fields(self):
        """Test TypedDictErrorData with partial fields."""
        error_data: TypedDictErrorData = {
            "error_level_count": 10,
            "warning_count": 2,
        }

        assert error_data["error_level_count"] == 10
        assert error_data["warning_count"] == 2
        # critical_error_count not specified, should be fine

    def test_typed_dict_error_data_single_field(self):
        """Test TypedDictErrorData with single field."""
        error_data: TypedDictErrorData = {
            "critical_error_count": 0,
        }

        assert error_data["critical_error_count"] == 0

    def test_typed_dict_error_data_zero_counts(self):
        """Test TypedDictErrorData with zero counts."""
        error_data: TypedDictErrorData = {
            "error_level_count": 0,
            "warning_count": 0,
            "critical_error_count": 0,
        }

        assert error_data["error_level_count"] == 0
        assert error_data["warning_count"] == 0
        assert error_data["critical_error_count"] == 0

    def test_typed_dict_error_data_high_counts(self):
        """Test TypedDictErrorData with high counts."""
        error_data: TypedDictErrorData = {
            "error_level_count": 1000,
            "warning_count": 500,
            "critical_error_count": 50,
        }

        assert error_data["error_level_count"] == 1000
        assert error_data["warning_count"] == 500
        assert error_data["critical_error_count"] == 50

    def test_typed_dict_error_data_field_types(self):
        """Test that all fields are integers."""
        error_data: TypedDictErrorData = {
            "error_level_count": 1,
            "warning_count": 2,
            "critical_error_count": 3,
        }

        assert isinstance(error_data["error_level_count"], int)
        assert isinstance(error_data["warning_count"], int)
        assert isinstance(error_data["critical_error_count"], int)

    def test_typed_dict_error_data_negative_counts(self):
        """Test TypedDictErrorData with negative counts (edge case)."""
        error_data: TypedDictErrorData = {
            "error_level_count": -1,
            "warning_count": -5,
            "critical_error_count": -10,
        }

        # TypedDict allows negative values, though they might not be semantically correct
        assert error_data["error_level_count"] == -1
        assert error_data["warning_count"] == -5
        assert error_data["critical_error_count"] == -10

    def test_typed_dict_error_data_analytics_use_case(self):
        """Test TypedDictErrorData in analytics context."""
        # Simulate analytics data
        analytics_data: TypedDictErrorData = {
            "error_level_count": 25,
            "warning_count": 12,
            "critical_error_count": 3,
        }

        total_issues = (
            analytics_data["error_level_count"]
            + analytics_data["warning_count"]
            + analytics_data["critical_error_count"]
        )

        assert total_issues == 40
        assert (
            analytics_data["critical_error_count"] < analytics_data["error_level_count"]
        )
        assert analytics_data["error_level_count"] > analytics_data["warning_count"]
