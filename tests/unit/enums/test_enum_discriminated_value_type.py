"""Tests for EnumDiscriminatedValueType."""

import pytest

from omnibase_core.enums.enum_discriminated_value_type import EnumDiscriminatedValueType


@pytest.mark.unit
class TestEnumDiscriminatedValueTypeBasics:
    """Tests for basic EnumDiscriminatedValueType functionality."""

    def test_enum_values(self) -> None:
        """Test that all enum values are defined."""
        assert EnumDiscriminatedValueType.BOOL.value == "bool"
        assert EnumDiscriminatedValueType.FLOAT.value == "float"
        assert EnumDiscriminatedValueType.INT.value == "int"
        assert EnumDiscriminatedValueType.STR.value == "str"
        assert EnumDiscriminatedValueType.DICT.value == "dict"
        assert EnumDiscriminatedValueType.LIST.value == "list"

    def test_enum_str_representation(self) -> None:
        """Test string representation of enum values."""
        assert str(EnumDiscriminatedValueType.BOOL) == "bool"
        assert str(EnumDiscriminatedValueType.INT) == "int"
        assert str(EnumDiscriminatedValueType.STR) == "str"

    def test_enum_uniqueness(self) -> None:
        """Test that all enum values are unique."""
        values = [member.value for member in EnumDiscriminatedValueType]
        assert len(values) == len(set(values))

    def test_enum_member_count(self) -> None:
        """Test that enum has expected number of members."""
        assert len(EnumDiscriminatedValueType) == 6


@pytest.mark.unit
class TestEnumDiscriminatedValueTypeTypeChecking:
    """Tests for EnumDiscriminatedValueType type checking methods."""

    def test_is_primitive_type_true(self) -> None:
        """Test is_primitive_type for primitive types."""
        assert (
            EnumDiscriminatedValueType.is_primitive_type(
                EnumDiscriminatedValueType.BOOL
            )
            is True
        )
        assert (
            EnumDiscriminatedValueType.is_primitive_type(EnumDiscriminatedValueType.INT)
            is True
        )
        assert (
            EnumDiscriminatedValueType.is_primitive_type(
                EnumDiscriminatedValueType.FLOAT
            )
            is True
        )
        assert (
            EnumDiscriminatedValueType.is_primitive_type(EnumDiscriminatedValueType.STR)
            is True
        )

    def test_is_primitive_type_false(self) -> None:
        """Test is_primitive_type for collection types."""
        assert (
            EnumDiscriminatedValueType.is_primitive_type(
                EnumDiscriminatedValueType.DICT
            )
            is False
        )
        assert (
            EnumDiscriminatedValueType.is_primitive_type(
                EnumDiscriminatedValueType.LIST
            )
            is False
        )

    def test_is_numeric_type_true(self) -> None:
        """Test is_numeric_type for numeric types."""
        assert (
            EnumDiscriminatedValueType.is_numeric_type(EnumDiscriminatedValueType.INT)
            is True
        )
        assert (
            EnumDiscriminatedValueType.is_numeric_type(EnumDiscriminatedValueType.FLOAT)
            is True
        )

    def test_is_numeric_type_false(self) -> None:
        """Test is_numeric_type for non-numeric types."""
        assert (
            EnumDiscriminatedValueType.is_numeric_type(EnumDiscriminatedValueType.BOOL)
            is False
        )
        assert (
            EnumDiscriminatedValueType.is_numeric_type(EnumDiscriminatedValueType.STR)
            is False
        )
        assert (
            EnumDiscriminatedValueType.is_numeric_type(EnumDiscriminatedValueType.DICT)
            is False
        )
        assert (
            EnumDiscriminatedValueType.is_numeric_type(EnumDiscriminatedValueType.LIST)
            is False
        )

    def test_is_collection_type_true(self) -> None:
        """Test is_collection_type for collection types."""
        assert (
            EnumDiscriminatedValueType.is_collection_type(
                EnumDiscriminatedValueType.DICT
            )
            is True
        )
        assert (
            EnumDiscriminatedValueType.is_collection_type(
                EnumDiscriminatedValueType.LIST
            )
            is True
        )

    def test_is_collection_type_false(self) -> None:
        """Test is_collection_type for non-collection types."""
        assert (
            EnumDiscriminatedValueType.is_collection_type(
                EnumDiscriminatedValueType.BOOL
            )
            is False
        )
        assert (
            EnumDiscriminatedValueType.is_collection_type(
                EnumDiscriminatedValueType.INT
            )
            is False
        )
        assert (
            EnumDiscriminatedValueType.is_collection_type(
                EnumDiscriminatedValueType.FLOAT
            )
            is False
        )
        assert (
            EnumDiscriminatedValueType.is_collection_type(
                EnumDiscriminatedValueType.STR
            )
            is False
        )


@pytest.mark.unit
class TestEnumDiscriminatedValueTypeGetters:
    """Tests for EnumDiscriminatedValueType getter methods."""

    def test_get_primitive_types(self) -> None:
        """Test get_primitive_types returns all primitive types."""
        primitive_types = EnumDiscriminatedValueType.get_primitive_types()
        assert len(primitive_types) == 4
        assert EnumDiscriminatedValueType.BOOL in primitive_types
        assert EnumDiscriminatedValueType.INT in primitive_types
        assert EnumDiscriminatedValueType.FLOAT in primitive_types
        assert EnumDiscriminatedValueType.STR in primitive_types
        assert EnumDiscriminatedValueType.DICT not in primitive_types
        assert EnumDiscriminatedValueType.LIST not in primitive_types

    def test_get_numeric_types(self) -> None:
        """Test get_numeric_types returns all numeric types."""
        numeric_types = EnumDiscriminatedValueType.get_numeric_types()
        assert len(numeric_types) == 2
        assert EnumDiscriminatedValueType.INT in numeric_types
        assert EnumDiscriminatedValueType.FLOAT in numeric_types
        assert EnumDiscriminatedValueType.BOOL not in numeric_types
        assert EnumDiscriminatedValueType.STR not in numeric_types

    def test_get_collection_types(self) -> None:
        """Test get_collection_types returns all collection types."""
        collection_types = EnumDiscriminatedValueType.get_collection_types()
        assert len(collection_types) == 2
        assert EnumDiscriminatedValueType.DICT in collection_types
        assert EnumDiscriminatedValueType.LIST in collection_types
        assert EnumDiscriminatedValueType.BOOL not in collection_types
        assert EnumDiscriminatedValueType.INT not in collection_types


@pytest.mark.unit
class TestEnumDiscriminatedValueTypeEdgeCases:
    """Tests for EnumDiscriminatedValueType edge cases."""

    def test_enum_comparison(self) -> None:
        """Test enum value comparison."""
        assert EnumDiscriminatedValueType.BOOL == EnumDiscriminatedValueType.BOOL
        assert EnumDiscriminatedValueType.INT != EnumDiscriminatedValueType.STR  # type: ignore[comparison-overlap]

    def test_enum_identity(self) -> None:
        """Test enum identity."""
        assert EnumDiscriminatedValueType.BOOL is EnumDiscriminatedValueType.BOOL
        assert EnumDiscriminatedValueType.INT is not EnumDiscriminatedValueType.FLOAT  # type: ignore[comparison-overlap]

    def test_enum_value_access(self) -> None:
        """Test accessing enum value attribute."""
        assert EnumDiscriminatedValueType.BOOL.value == "bool"
        assert EnumDiscriminatedValueType.INT.value == "int"

    def test_enum_iteration(self) -> None:
        """Test iterating over enum members."""
        members = list(EnumDiscriminatedValueType)
        assert len(members) == 6
        assert EnumDiscriminatedValueType.BOOL in members
        assert EnumDiscriminatedValueType.LIST in members
