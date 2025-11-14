"""
Test suite for TypedDictDebugInfoData.
"""

from datetime import datetime

import pytest

from omnibase_core.types.typed_dict_debug_info_data import TypedDictDebugInfoData


class TestTypedDictDebugInfoData:
    """Test TypedDictDebugInfoData functionality."""

    def test_typed_dict_debug_info_data_empty(self):
        """Test creating empty TypedDictDebugInfoData."""
        data: TypedDictDebugInfoData = {}

        assert isinstance(data, dict)
        assert len(data) == 0

    def test_typed_dict_debug_info_data_with_key_only(self):
        """Test TypedDictDebugInfoData with key only."""
        data: TypedDictDebugInfoData = {"key": "debug_key_1"}

        assert data["key"] == "debug_key_1"
        assert isinstance(data["key"], str)

    def test_typed_dict_debug_info_data_with_value_only(self):
        """Test TypedDictDebugInfoData with value only."""
        data: TypedDictDebugInfoData = {"value": "debug_value_1"}

        assert data["value"] == "debug_value_1"
        assert isinstance(data["value"], str)

    def test_typed_dict_debug_info_data_with_timestamp_only(self):
        """Test TypedDictDebugInfoData with timestamp only."""
        now = datetime.now()
        data: TypedDictDebugInfoData = {"timestamp": now}

        assert data["timestamp"] == now
        assert isinstance(data["timestamp"], datetime)

    def test_typed_dict_debug_info_data_with_category_only(self):
        """Test TypedDictDebugInfoData with category only."""
        data: TypedDictDebugInfoData = {"category": "performance"}

        assert data["category"] == "performance"
        assert isinstance(data["category"], str)

    def test_typed_dict_debug_info_data_complete(self):
        """Test TypedDictDebugInfoData with all fields."""
        now = datetime.now()
        data: TypedDictDebugInfoData = {
            "key": "complete_debug_key",
            "value": "complete_debug_value",
            "timestamp": now,
            "category": "system",
        }

        assert data["key"] == "complete_debug_key"
        assert data["value"] == "complete_debug_value"
        assert data["timestamp"] == now
        assert data["category"] == "system"

    def test_typed_dict_debug_info_data_partial_fields(self):
        """Test TypedDictDebugInfoData with some fields."""
        data: TypedDictDebugInfoData = {"key": "partial_key", "value": "partial_value"}

        assert data["key"] == "partial_key"
        assert data["value"] == "partial_value"
        assert "timestamp" not in data
        assert "category" not in data

    def test_typed_dict_debug_info_data_different_categories(self):
        """Test TypedDictDebugInfoData with different categories."""
        categories = ["performance", "error", "warning", "info", "debug", "trace"]

        for category in categories:
            data: TypedDictDebugInfoData = {
                "key": f"key_for_{category}",
                "value": f"value_for_{category}",
                "category": category,
            }
            assert data["category"] == category

    def test_typed_dict_debug_info_data_timestamp_formats(self):
        """Test TypedDictDebugInfoData with different timestamp formats."""
        now = datetime.now()
        specific_time = datetime(2024, 1, 15, 10, 30, 45)
        iso_time = datetime.fromisoformat("2024-01-01T12:00:00")

        # Test with current time
        data1: TypedDictDebugInfoData = {
            "key": "current_time_key",
            "value": "current_time_value",
            "timestamp": now,
        }
        assert data1["timestamp"] == now

        # Test with specific time
        data2: TypedDictDebugInfoData = {
            "key": "specific_time_key",
            "value": "specific_time_value",
            "timestamp": specific_time,
        }
        assert data2["timestamp"] == specific_time

        # Test with ISO time
        data3: TypedDictDebugInfoData = {
            "key": "iso_time_key",
            "value": "iso_time_value",
            "timestamp": iso_time,
        }
        assert data3["timestamp"] == iso_time

    def test_typed_dict_debug_info_data_long_strings(self):
        """Test TypedDictDebugInfoData with long string values."""
        long_key = "very_long_debug_key_" + "x" * 100
        long_value = "very_long_debug_value_" + "y" * 200
        long_category = "very_long_category_name_" + "z" * 50

        data: TypedDictDebugInfoData = {
            "key": long_key,
            "value": long_value,
            "category": long_category,
        }

        assert data["key"] == long_key
        assert data["value"] == long_value
        assert data["category"] == long_category

    def test_typed_dict_debug_info_data_special_characters(self):
        """Test TypedDictDebugInfoData with special characters."""
        data: TypedDictDebugInfoData = {
            "key": "key-with-special-chars_123",
            "value": "value$with%special&chars",
            "category": "category@with#special*chars",
        }

        assert data["key"] == "key-with-special-chars_123"
        assert data["value"] == "value$with%special&chars"
        assert data["category"] == "category@with#special*chars"

    def test_typed_dict_debug_info_data_unicode(self):
        """Test TypedDictDebugInfoData with unicode characters."""
        data: TypedDictDebugInfoData = {
            "key": "调试键_测试",
            "value": "调试值_测试",
            "category": "调试类别",
        }

        assert data["key"] == "调试键_测试"
        assert data["value"] == "调试值_测试"
        assert data["category"] == "调试类别"

    def test_typed_dict_debug_info_data_empty_strings(self):
        """Test TypedDictDebugInfoData with empty string values."""
        data: TypedDictDebugInfoData = {"key": "", "value": "", "category": ""}

        assert data["key"] == ""
        assert data["value"] == ""
        assert data["category"] == ""

    def test_typed_dict_debug_info_data_type_annotations(self):
        """Test that all fields have correct type annotations."""
        data: TypedDictDebugInfoData = {
            "key": "type_test_key",
            "value": "type_test_value",
            "timestamp": datetime.now(),
            "category": "type_test",
        }

        assert isinstance(data["key"], str)
        assert isinstance(data["value"], str)
        assert isinstance(data["timestamp"], datetime)
        assert isinstance(data["category"], str)

    def test_typed_dict_debug_info_data_mutability(self):
        """Test that TypedDictDebugInfoData behaves like a regular dict."""
        data: TypedDictDebugInfoData = {"key": "mutable_key"}

        # Should be able to modify like a regular dict
        data["value"] = "mutable_value"
        data["timestamp"] = datetime.now()
        data["category"] = "mutable_category"
        data["key"] = "modified_key"

        assert data["key"] == "modified_key"
        assert data["value"] == "mutable_value"
        assert isinstance(data["timestamp"], datetime)
        assert data["category"] == "mutable_category"

    def test_typed_dict_debug_info_data_equality(self):
        """Test equality comparison between instances."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        data1: TypedDictDebugInfoData = {
            "key": "equality_test_key",
            "value": "equality_test_value",
            "timestamp": base_time,
            "category": "equality_test",
        }

        data2: TypedDictDebugInfoData = {
            "key": "equality_test_key",
            "value": "equality_test_value",
            "timestamp": base_time,
            "category": "equality_test",
        }

        assert data1 == data2

        # Modify one field
        data2["value"] = "different_value"
        assert data1 != data2

    def test_typed_dict_debug_info_data_edge_cases(self):
        """Test edge cases for debug info data."""
        # Test with minimum datetime
        data: TypedDictDebugInfoData = {
            "key": "edge_case_key",
            "value": "edge_case_value",
            "timestamp": datetime.min,
            "category": "edge_case",
        }

        assert data["key"] == "edge_case_key"
        assert data["value"] == "edge_case_value"
        assert data["timestamp"] == datetime.min
        assert data["category"] == "edge_case"

    def test_typed_dict_debug_info_data_optional_fields(self):
        """Test that all fields are optional (total=False)."""
        # Test with no fields
        empty_data: TypedDictDebugInfoData = {}
        assert len(empty_data) == 0

        # Test with one field
        single_field_data: TypedDictDebugInfoData = {"key": "single_field_key"}
        assert len(single_field_data) == 1

        # Test with two fields
        two_field_data: TypedDictDebugInfoData = {
            "key": "two_field_key",
            "value": "two_field_value",
        }
        assert len(two_field_data) == 2

    def test_typed_dict_debug_info_data_nested_access(self):
        """Test accessing nested properties."""
        data: TypedDictDebugInfoData = {
            "key": "nested_access_key",
            "value": "nested_access_value",
            "timestamp": datetime.now(),
            "category": "nested_access",
        }

        # Test accessing all fields
        fields = ["key", "value", "timestamp", "category"]
        for field in fields:
            assert field in data
            if field == "timestamp":
                assert isinstance(data[field], datetime)
            else:
                assert isinstance(data[field], str)
