"""
Unit tests for EnumCellType.

Tests all aspects of the cell type enum including:
- Enum value validation
- Helper methods for cell type classification
- String representation
- JSON serialization compatibility
- Pydantic integration
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_cell_type import EnumCellType


@pytest.mark.unit
class TestEnumCellType:
    """Test cases for EnumCellType."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "CODE": "code",
            "MARKDOWN": "markdown",
        }

        for name, value in expected_values.items():
            cell_type = getattr(EnumCellType, name)
            assert cell_type.value == value
            assert str(cell_type) == value

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumCellType.CODE, str)
        assert EnumCellType.CODE == "code"
        assert isinstance(EnumCellType.MARKDOWN, str)
        assert EnumCellType.MARKDOWN == "markdown"

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumCellType.CODE) == "code"
        assert str(EnumCellType.MARKDOWN) == "markdown"

    def test_is_executable(self):
        """Test the is_executable class method."""
        assert EnumCellType.is_executable(EnumCellType.CODE) is True
        assert EnumCellType.is_executable(EnumCellType.MARKDOWN) is False

    def test_is_documentation(self):
        """Test the is_documentation class method."""
        assert EnumCellType.is_documentation(EnumCellType.MARKDOWN) is True
        assert EnumCellType.is_documentation(EnumCellType.CODE) is False

    def test_supports_syntax_highlighting(self):
        """Test the supports_syntax_highlighting class method."""
        # Both code and markdown support syntax highlighting
        assert EnumCellType.supports_syntax_highlighting(EnumCellType.CODE) is True
        assert EnumCellType.supports_syntax_highlighting(EnumCellType.MARKDOWN) is True

    def test_produces_output(self):
        """Test the produces_output class method."""
        assert EnumCellType.produces_output(EnumCellType.CODE) is True
        assert EnumCellType.produces_output(EnumCellType.MARKDOWN) is False

    def test_supports_rich_text(self):
        """Test the supports_rich_text class method."""
        assert EnumCellType.supports_rich_text(EnumCellType.MARKDOWN) is True
        assert EnumCellType.supports_rich_text(EnumCellType.CODE) is False

    def test_get_cell_description(self):
        """Test the get_cell_description class method."""
        code_desc = EnumCellType.get_cell_description(EnumCellType.CODE)
        assert "Executable code cell" in code_desc
        assert "syntax highlighting" in code_desc

        markdown_desc = EnumCellType.get_cell_description(EnumCellType.MARKDOWN)
        assert "Rich text documentation" in markdown_desc
        assert "markdown support" in markdown_desc

    def test_get_typical_content(self):
        """Test the get_typical_content class method."""
        code_content = EnumCellType.get_typical_content(EnumCellType.CODE)
        assert "Python code" in code_content
        assert "function definitions" in code_content

        markdown_content = EnumCellType.get_typical_content(EnumCellType.MARKDOWN)
        assert "Documentation" in markdown_content
        assert "formatted text" in markdown_content

    def test_get_editor_mode(self):
        """Test the get_editor_mode class method."""
        code_mode = EnumCellType.get_editor_mode(EnumCellType.CODE)
        assert code_mode == "python"

        markdown_mode = EnumCellType.get_editor_mode(EnumCellType.MARKDOWN)
        assert markdown_mode == "markdown"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumCellType.CODE == EnumCellType.CODE
        assert EnumCellType.MARKDOWN != EnumCellType.CODE

    def test_enum_membership(self):
        """Test enum membership checking."""
        assert EnumCellType.CODE in EnumCellType
        assert EnumCellType.MARKDOWN in EnumCellType

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        cell_types = list(EnumCellType)
        assert len(cell_types) == 2

        cell_values = [c.value for c in cell_types]
        assert set(cell_values) == {"code", "markdown"}

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        cell_type = EnumCellType.CODE
        json_str = json.dumps(cell_type, default=str)
        assert json_str == '"code"'

        # Test in dictionary
        data = {"cell_type": EnumCellType.MARKDOWN}
        json_str = json.dumps(data, default=str)
        assert '"cell_type": "markdown"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class CellConfig(BaseModel):
            cell_type: EnumCellType

        # Test valid enum assignment
        config = CellConfig(cell_type=EnumCellType.CODE)
        assert config.cell_type == EnumCellType.CODE

        # Test string assignment (should work due to str inheritance)
        config = CellConfig(cell_type="markdown")
        assert config.cell_type == EnumCellType.MARKDOWN

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            CellConfig(cell_type="invalid_type")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class CellConfig(BaseModel):
            cell_type: EnumCellType

        config = CellConfig(cell_type=EnumCellType.CODE)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"cell_type": "code"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"cell_type":"code"}'

    def test_comprehensive_cell_type_characteristics(self):
        """Test comprehensive characteristics of each cell type."""
        # CODE cells: executable, produce output, support syntax highlighting
        assert EnumCellType.is_executable(EnumCellType.CODE) is True
        assert EnumCellType.produces_output(EnumCellType.CODE) is True
        assert EnumCellType.supports_syntax_highlighting(EnumCellType.CODE) is True
        assert EnumCellType.supports_rich_text(EnumCellType.CODE) is False
        assert EnumCellType.is_documentation(EnumCellType.CODE) is False

        # MARKDOWN cells: documentation, rich text, support syntax highlighting
        assert EnumCellType.is_documentation(EnumCellType.MARKDOWN) is True
        assert EnumCellType.supports_rich_text(EnumCellType.MARKDOWN) is True
        assert EnumCellType.supports_syntax_highlighting(EnumCellType.MARKDOWN) is True
        assert EnumCellType.is_executable(EnumCellType.MARKDOWN) is False
        assert EnumCellType.produces_output(EnumCellType.MARKDOWN) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
