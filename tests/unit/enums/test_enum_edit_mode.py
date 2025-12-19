"""Test EnumEditMode enum."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_edit_mode import EnumEditMode


@pytest.mark.unit
class TestEnumEditMode:
    """Test EnumEditMode functionality."""

    def test_enum_inheritance(self):
        """Test enum inheritance."""
        assert issubclass(EnumEditMode, str)
        assert issubclass(EnumEditMode, Enum)

    def test_enum_values(self):
        """Test enum values."""
        assert EnumEditMode.REPLACE == "replace"
        assert EnumEditMode.INSERT == "insert"
        assert EnumEditMode.DELETE == "delete"

    def test_enum_string_behavior(self):
        """Test enum string behavior."""
        mode = EnumEditMode.REPLACE
        assert isinstance(mode, str)
        assert mode == "replace"
        assert len(mode) == 7
        assert mode.startswith("repl")

    def test_enum_iteration(self):
        """Test enum iteration."""
        values = list(EnumEditMode)
        assert len(values) == 3
        assert EnumEditMode.REPLACE in values
        assert EnumEditMode.INSERT in values
        assert EnumEditMode.DELETE in values

    def test_enum_membership(self):
        """Test enum membership."""
        assert "replace" in EnumEditMode
        assert "insert" in EnumEditMode
        assert "delete" in EnumEditMode
        assert "invalid_mode" not in EnumEditMode

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumEditMode.REPLACE == "replace"
        assert EnumEditMode.REPLACE != "insert"
        assert EnumEditMode.DELETE < EnumEditMode.INSERT

    def test_enum_serialization(self):
        """Test enum serialization."""
        mode = EnumEditMode.INSERT
        serialized = mode.value
        assert serialized == "insert"
        import json

        json_str = json.dumps(mode)
        assert json_str == '"insert"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        mode = EnumEditMode("delete")
        assert mode == EnumEditMode.DELETE

    def test_enum_invalid_value(self):
        """Test enum with invalid value."""
        with pytest.raises(ValueError):
            EnumEditMode("invalid_mode")

    def test_enum_all_values(self):
        """Test all enum values."""
        expected_values = ["replace", "insert", "delete"]
        actual_values = [e.value for e in EnumEditMode]
        assert set(actual_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test enum docstring."""
        assert EnumEditMode.__doc__ is not None
        assert "edit mode discriminators" in EnumEditMode.__doc__

    def test_enum_unique_decorator(self):
        """Test that enum has unique decorator."""
        assert hasattr(EnumEditMode, "__annotations__")

    def test_str_method(self):
        """Test __str__ method."""
        mode = EnumEditMode.DELETE
        assert str(mode) == "delete"
        assert str(mode) == mode.value

    def test_is_destructive(self):
        """Test is_destructive method."""
        assert EnumEditMode.is_destructive(EnumEditMode.REPLACE) is True
        assert EnumEditMode.is_destructive(EnumEditMode.DELETE) is True
        assert EnumEditMode.is_destructive(EnumEditMode.INSERT) is False

    def test_is_additive(self):
        """Test is_additive method."""
        assert EnumEditMode.is_additive(EnumEditMode.INSERT) is True
        assert EnumEditMode.is_additive(EnumEditMode.REPLACE) is False
        assert EnumEditMode.is_additive(EnumEditMode.DELETE) is False

    def test_requires_content(self):
        """Test requires_content method."""
        assert EnumEditMode.requires_content(EnumEditMode.REPLACE) is True
        assert EnumEditMode.requires_content(EnumEditMode.INSERT) is True
        assert EnumEditMode.requires_content(EnumEditMode.DELETE) is False

    def test_requires_target(self):
        """Test requires_target method."""
        assert EnumEditMode.requires_target(EnumEditMode.REPLACE) is True
        assert EnumEditMode.requires_target(EnumEditMode.DELETE) is True
        assert EnumEditMode.requires_target(EnumEditMode.INSERT) is False

    def test_changes_structure(self):
        """Test changes_structure method."""
        assert EnumEditMode.changes_structure(EnumEditMode.INSERT) is True
        assert EnumEditMode.changes_structure(EnumEditMode.DELETE) is True
        assert EnumEditMode.changes_structure(EnumEditMode.REPLACE) is False

    def test_get_operation_description(self):
        """Test get_operation_description method."""
        assert (
            EnumEditMode.get_operation_description(EnumEditMode.REPLACE)
            == "Replace existing content with new content"
        )
        assert (
            EnumEditMode.get_operation_description(EnumEditMode.INSERT)
            == "Insert new content at specified position"
        )
        assert (
            EnumEditMode.get_operation_description(EnumEditMode.DELETE)
            == "Remove existing content"
        )

    def test_get_required_parameters(self):
        """Test get_required_parameters method."""
        replace_params = EnumEditMode.get_required_parameters(EnumEditMode.REPLACE)
        assert "target_identifier" in replace_params
        assert "new_content" in replace_params
        assert len(replace_params) == 2

        insert_params = EnumEditMode.get_required_parameters(EnumEditMode.INSERT)
        assert "position_identifier" in insert_params
        assert "new_content" in insert_params
        assert len(insert_params) == 2

        delete_params = EnumEditMode.get_required_parameters(EnumEditMode.DELETE)
        assert "target_identifier" in delete_params
        assert len(delete_params) == 1

    def test_edit_mode_classification(self):
        """Test edit mode classification."""
        # Test destructive modes
        destructive_modes = [EnumEditMode.REPLACE, EnumEditMode.DELETE]
        for mode in destructive_modes:
            assert EnumEditMode.is_destructive(mode) is True
            assert EnumEditMode.requires_target(mode) is True

        # Test additive mode
        assert EnumEditMode.is_additive(EnumEditMode.INSERT) is True
        assert EnumEditMode.requires_content(EnumEditMode.INSERT) is True
        assert EnumEditMode.changes_structure(EnumEditMode.INSERT) is True

        # Test content requirements
        content_required = [EnumEditMode.REPLACE, EnumEditMode.INSERT]
        for mode in content_required:
            assert EnumEditMode.requires_content(mode) is True

        # Test structure changes
        structure_changing = [EnumEditMode.INSERT, EnumEditMode.DELETE]
        for mode in structure_changing:
            assert EnumEditMode.changes_structure(mode) is True

    def test_edit_mode_workflow(self):
        """Test edit mode workflow scenarios."""
        # Replace workflow
        replace_mode = EnumEditMode.REPLACE
        assert EnumEditMode.is_destructive(replace_mode) is True
        assert EnumEditMode.requires_content(replace_mode) is True
        assert EnumEditMode.requires_target(replace_mode) is True
        assert EnumEditMode.changes_structure(replace_mode) is False

        # Insert workflow
        insert_mode = EnumEditMode.INSERT
        assert EnumEditMode.is_destructive(insert_mode) is False
        assert EnumEditMode.is_additive(insert_mode) is True
        assert EnumEditMode.requires_content(insert_mode) is True
        assert EnumEditMode.requires_target(insert_mode) is False
        assert EnumEditMode.changes_structure(insert_mode) is True

        # Delete workflow
        delete_mode = EnumEditMode.DELETE
        assert EnumEditMode.is_destructive(delete_mode) is True
        assert EnumEditMode.requires_content(delete_mode) is False
        assert EnumEditMode.requires_target(delete_mode) is True
        assert EnumEditMode.changes_structure(delete_mode) is True
