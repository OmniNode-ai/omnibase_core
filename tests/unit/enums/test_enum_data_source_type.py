"""
Tests for EnumDataSourceType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_data_source_type import EnumDataSourceType


@pytest.mark.unit
class TestEnumDataSourceType:
    """Test cases for EnumDataSourceType enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumDataSourceType.FILE_SYSTEM == "FILE_SYSTEM"
        assert EnumDataSourceType.DATABASE_RECORD == "DATABASE_RECORD"
        assert EnumDataSourceType.API_REQUEST == "API_REQUEST"
        assert EnumDataSourceType.SCHEDULED_JOB == "SCHEDULED_JOB"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDataSourceType, str)
        assert issubclass(EnumDataSourceType, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        source_type = EnumDataSourceType.FILE_SYSTEM
        assert isinstance(source_type, str)
        assert source_type == "FILE_SYSTEM"
        assert len(source_type) == 11
        assert source_type.startswith("FILE")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDataSourceType)
        assert len(values) == 4
        assert EnumDataSourceType.FILE_SYSTEM in values
        assert EnumDataSourceType.SCHEDULED_JOB in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "FILE_SYSTEM" in EnumDataSourceType
        assert "invalid_type" not in EnumDataSourceType

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        type1 = EnumDataSourceType.FILE_SYSTEM
        type2 = EnumDataSourceType.DATABASE_RECORD

        assert type1 != type2
        assert type1 == "FILE_SYSTEM"
        assert type2 == "DATABASE_RECORD"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        source_type = EnumDataSourceType.API_REQUEST
        serialized = source_type.value
        assert serialized == "API_REQUEST"

        # Test JSON serialization
        import json

        json_str = json.dumps(source_type)
        assert json_str == '"API_REQUEST"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        source_type = EnumDataSourceType("SCHEDULED_JOB")
        assert source_type == EnumDataSourceType.SCHEDULED_JOB

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDataSourceType("invalid_type")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "FILE_SYSTEM",
            "DATABASE_RECORD",
            "API_REQUEST",
            "SCHEDULED_JOB",
        }

        actual_values = {member.value for member in EnumDataSourceType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Types of data sources in the pipeline" in EnumDataSourceType.__doc__

    def test_enum_data_source_types(self):
        """Test that enum covers typical data source types."""
        # Test file system source
        assert EnumDataSourceType.FILE_SYSTEM in EnumDataSourceType

        # Test database source
        assert EnumDataSourceType.DATABASE_RECORD in EnumDataSourceType

        # Test API source
        assert EnumDataSourceType.API_REQUEST in EnumDataSourceType

        # Test scheduled job source
        assert EnumDataSourceType.SCHEDULED_JOB in EnumDataSourceType
