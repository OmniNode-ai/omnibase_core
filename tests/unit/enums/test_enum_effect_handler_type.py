"""
Tests for EnumEffectHandlerType enum.

Part of the Contract-Driven NodeEffect v1.0 implementation (OMN-521).
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


class TestEnumEffectHandlerType:
    """Test cases for EnumEffectHandlerType enum."""

    def test_handler_type_values(self):
        """Test that all 4 handler type values exist with correct string values."""
        assert EnumEffectHandlerType.HTTP == "http"
        assert EnumEffectHandlerType.DB == "db"
        assert EnumEffectHandlerType.KAFKA == "kafka"
        assert EnumEffectHandlerType.FILESYSTEM == "filesystem"

    def test_enum_inherits_from_str(self):
        """Test that enum inherits from str for Pydantic serialization."""
        assert issubclass(EnumEffectHandlerType, str)
        assert issubclass(EnumEffectHandlerType, Enum)

    def test_values_class_method(self):
        """Test values() class method returns all handler type values."""
        values = EnumEffectHandlerType.values()
        assert isinstance(values, list)
        assert len(values) == 4
        assert "http" in values
        assert "db" in values
        assert "kafka" in values
        assert "filesystem" in values

    def test_enum_count(self):
        """Test that enum has exactly 4 members."""
        all_members = list(EnumEffectHandlerType)
        assert len(all_members) == 4

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumEffectHandlerType)
        assert EnumEffectHandlerType.HTTP in values
        assert EnumEffectHandlerType.DB in values
        assert EnumEffectHandlerType.KAFKA in values
        assert EnumEffectHandlerType.FILESYSTEM in values

    def test_enum_membership(self):
        """Test membership testing with string values."""
        assert "http" in EnumEffectHandlerType
        assert "db" in EnumEffectHandlerType
        assert "kafka" in EnumEffectHandlerType
        assert "filesystem" in EnumEffectHandlerType
        assert "invalid" not in EnumEffectHandlerType
        assert "database" not in EnumEffectHandlerType  # Note: it's "db", not "database"

    def test_enum_comparison(self):
        """Test enum comparison with string values."""
        assert EnumEffectHandlerType.HTTP == "http"
        assert EnumEffectHandlerType.DB == "db"
        assert EnumEffectHandlerType.KAFKA == "kafka"
        assert EnumEffectHandlerType.FILESYSTEM == "filesystem"

    def test_enum_serialization(self):
        """Test enum serialization via .value attribute."""
        assert EnumEffectHandlerType.HTTP.value == "http"
        assert EnumEffectHandlerType.DB.value == "db"
        assert EnumEffectHandlerType.KAFKA.value == "kafka"
        assert EnumEffectHandlerType.FILESYSTEM.value == "filesystem"

    def test_enum_deserialization(self):
        """Test enum deserialization from string values."""
        assert EnumEffectHandlerType("http") == EnumEffectHandlerType.HTTP
        assert EnumEffectHandlerType("db") == EnumEffectHandlerType.DB
        assert EnumEffectHandlerType("kafka") == EnumEffectHandlerType.KAFKA
        assert EnumEffectHandlerType("filesystem") == EnumEffectHandlerType.FILESYSTEM

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEffectHandlerType("invalid")

        with pytest.raises(ValueError):
            EnumEffectHandlerType("database")  # Should be "db"

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        # Because (str, Enum), the enum value IS a string
        http = EnumEffectHandlerType.HTTP

        # Can be used in string operations
        assert http.upper() == "HTTP"
        assert http.startswith("h")
        assert len(http) == 4

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        docstring = EnumEffectHandlerType.__doc__
        assert docstring is not None
        assert "SINGLE SOURCE OF TRUTH" in docstring
        assert "Pydantic" in docstring

    def test_values_method_returns_fresh_list(self):
        """Test that values() returns a new list each time."""
        values1 = EnumEffectHandlerType.values()
        values2 = EnumEffectHandlerType.values()
        assert values1 == values2
        assert values1 is not values2  # Different list objects


class TestEnumEffectHandlerTypePydanticIntegration:
    """Test Pydantic serialization compatibility."""

    def test_pydantic_model_serialization(self):
        """Test enum serialization in a Pydantic model context."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            handler_type: EnumEffectHandlerType

        model = TestModel(handler_type=EnumEffectHandlerType.HTTP)
        serialized = model.model_dump()
        assert serialized["handler_type"] == "http"

    def test_pydantic_model_deserialization(self):
        """Test enum deserialization in a Pydantic model context."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            handler_type: EnumEffectHandlerType

        # Deserialize from string
        model = TestModel(handler_type="db")
        assert model.handler_type == EnumEffectHandlerType.DB

        # Deserialize from enum
        model = TestModel(handler_type=EnumEffectHandlerType.KAFKA)
        assert model.handler_type == EnumEffectHandlerType.KAFKA

    def test_pydantic_json_serialization(self):
        """Test enum JSON serialization round-trip."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            handler_type: EnumEffectHandlerType

        model = TestModel(handler_type=EnumEffectHandlerType.FILESYSTEM)
        json_str = model.model_dump_json()
        assert '"handler_type":"filesystem"' in json_str

        # Round-trip
        restored = TestModel.model_validate_json(json_str)
        assert restored.handler_type == EnumEffectHandlerType.FILESYSTEM


class TestEnumEffectHandlerTypeExport:
    """Test enum is properly exported from omnibase_core.enums."""

    def test_import_from_enums_package(self):
        """Test enum can be imported from omnibase_core.enums."""
        from omnibase_core.enums import EnumEffectHandlerType as ImportedEnum

        assert ImportedEnum is EnumEffectHandlerType
        assert ImportedEnum.HTTP == "http"
