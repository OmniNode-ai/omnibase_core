"""
Unit tests for ModelCliAction.

Tests all aspects of the CLI action model including:
- Model instantiation and validation
- Field validation and type checking
- Serialization/deserialization
- Factory methods and business logic
- Edge cases and error conditions
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.omnibase_core.enums.enum_action_category import EnumActionCategory
from src.omnibase_core.models.cli.model_cli_action import ModelCliAction


class TestModelCliAction:
    """Test cases for ModelCliAction."""

    def test_model_instantiation_valid_data(self):
        """Test that model can be instantiated with valid data."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="deploy",
            node_id=node_id,
            node_name="test_node",
            description="Deploy the test node",
        )

        assert action.action_name == "deploy"
        assert action.node_id == node_id
        assert action.node_name == "test_node"
        assert action.description == "Deploy the test node"
        assert action.deprecated is False  # Default value
        assert action.category is None  # Default value
        assert isinstance(action.action_id, UUID)  # Auto-generated

    def test_model_instantiation_with_all_fields(self):
        """Test model instantiation with all fields provided."""
        node_id = uuid4()
        action_id = uuid4()
        action = ModelCliAction(
            action_id=action_id,
            action_name="configure",
            node_id=node_id,
            node_name="config_node",
            description="Configure the node settings",
            deprecated=True,
            category=EnumActionCategory.CONFIGURATION,
        )

        assert action.action_id == action_id
        assert action.action_name == "configure"
        assert action.node_id == node_id
        assert action.node_name == "config_node"
        assert action.description == "Configure the node settings"
        assert action.deprecated is True
        assert action.category == EnumActionCategory.CONFIGURATION

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        node_id = uuid4()

        # Missing action_name
        with pytest.raises(ValidationError) as exc_info:
            ModelCliAction(
                node_id=node_id, node_name="test_node", description="Test description"
            )
        assert "action_name" in str(exc_info.value)

        # Missing node_id
        with pytest.raises(ValidationError) as exc_info:
            ModelCliAction(
                action_name="test_action",
                node_name="test_node",
                description="Test description",
            )
        assert "node_id" in str(exc_info.value)

        # Missing node_name
        with pytest.raises(ValidationError) as exc_info:
            ModelCliAction(
                action_name="test_action",
                node_id=node_id,
                description="Test description",
            )
        assert "node_name" in str(exc_info.value)

        # Missing description
        with pytest.raises(ValidationError) as exc_info:
            ModelCliAction(
                action_name="test_action", node_id=node_id, node_name="test_node"
            )
        assert "description" in str(exc_info.value)

    def test_action_name_pattern_validation(self):
        """Test that action_name follows the required pattern."""
        # Valid patterns
        valid_names = [
            "deploy",
            "configure",
            "test_action",
            "action123",
            "a",
            "action_with_numbers_123",
        ]

        node_id = uuid4()
        for name in valid_names:
            action = ModelCliAction(
                action_name=name,
                node_id=node_id,
                node_name="test_node",
                description="Test description",
            )
            assert action.action_name == name

        # Invalid patterns
        invalid_names = [
            "Deploy",  # Starts with uppercase
            "123action",  # Starts with number
            "action-name",  # Contains hyphen
            "action.name",  # Contains dot
            "action name",  # Contains space
            "",  # Empty string
            "_action",  # Starts with underscore
        ]

        node_id = uuid4()
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ModelCliAction(
                    action_name=name,
                    node_id=node_id,
                    node_name="test_node",
                    description="Test description",
                )
            assert "pattern" in str(
                exc_info.value
            ).lower() or "string_pattern_mismatch" in str(exc_info.value)

    def test_field_types_validation(self):
        """Test that field types are properly validated."""
        node_id = uuid4()

        # Test non-string action_name
        with pytest.raises(ValidationError):
            ModelCliAction(
                action_name=123,
                node_id=node_id,
                node_name="test_node",
                description="Test description",
            )

        # Test invalid node_id type
        with pytest.raises(ValidationError):
            ModelCliAction(
                action_name="test_action",
                node_id="not-a-uuid",
                node_name="test_node",
                description="Test description",
            )

        # Test non-string node_name
        with pytest.raises(ValidationError):
            ModelCliAction(
                action_name="test_action",
                node_id=node_id,
                node_name=123,
                description="Test description",
            )

        # Test non-string description
        with pytest.raises(ValidationError):
            ModelCliAction(
                action_name="test_action",
                node_id=node_id,
                node_name="test_node",
                description=123,
            )

        # Test non-coercible deprecated value (Pydantic V2 can coerce some strings)
        with pytest.raises(ValidationError):
            ModelCliAction(
                action_name="test_action",
                node_id=node_id,
                node_name="test_node",
                description="Test description",
                deprecated=123,  # Should not be coercible to boolean
            )

    def test_from_contract_action_factory_method(self):
        """Test the from_contract_action factory method."""
        # Test with minimal parameters
        node_id = uuid4()
        action = ModelCliAction.from_contract_action(
            action_name="deploy", node_id=node_id, node_name="test_node"
        )

        assert action.action_name == "deploy"
        assert action.node_id == node_id
        assert action.node_name == "test_node"
        assert action.description == "deploy action for test_node"  # Auto-generated
        assert action.deprecated is False
        assert action.category is None
        assert isinstance(action.action_id, UUID)  # Auto-generated

        # Test with custom description
        node_id2 = uuid4()
        action = ModelCliAction.from_contract_action(
            action_name="configure",
            node_id=node_id2,
            node_name="config_node",
            description="Custom configuration action",
        )

        assert action.action_name == "configure"
        assert action.node_id == node_id2
        assert action.node_name == "config_node"
        assert action.description == "Custom configuration action"

        # Test with additional kwargs
        node_id3 = uuid4()
        action = ModelCliAction.from_contract_action(
            action_name="migrate",
            node_id=node_id3,
            node_name="migration_node",
            deprecated=True,
            category=EnumActionCategory.SYSTEM,
        )

        assert action.action_name == "migrate"
        assert action.node_id == node_id3
        assert action.node_name == "migration_node"
        assert action.description == "migrate action for migration_node"
        assert action.deprecated is True
        assert action.category == EnumActionCategory.SYSTEM

    def test_get_qualified_name_method(self):
        """Test the get_qualified_name method."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        qualified_name = action.get_qualified_name()
        assert qualified_name == "app_node:deploy"

    def test_get_globally_unique_id_method(self):
        """Test the get_globally_unique_id method."""
        node_id = uuid4()
        action_id = uuid4()
        action = ModelCliAction(
            action_id=action_id,
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        unique_id = action.get_globally_unique_id()
        assert unique_id == f"{node_id}:{action_id}"

    def test_matches_method(self):
        """Test the matches method."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        # Test positive matches
        assert action.matches("deploy") is True

        # Test negative matches
        assert action.matches("configure") is False
        assert action.matches("Deploy") is False  # Case sensitive
        assert action.matches("") is False
        assert action.matches("deploy_app") is False

    def test_matches_node_id_method(self):
        """Test the matches_node_id method."""
        node_id = uuid4()
        other_node_id = uuid4()
        action = ModelCliAction(
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        # Test positive match
        assert action.matches_node_id(node_id) is True

        # Test negative match
        assert action.matches_node_id(other_node_id) is False

    def test_matches_action_id_method(self):
        """Test the matches_action_id method."""
        node_id = uuid4()
        action_id = uuid4()
        other_action_id = uuid4()
        action = ModelCliAction(
            action_id=action_id,
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        # Test positive match
        assert action.matches_action_id(action_id) is True

        # Test negative match
        assert action.matches_action_id(other_action_id) is False

    def test_model_serialization(self):
        """Test model serialization to dict."""
        node_id = uuid4()
        action_id = uuid4()
        action = ModelCliAction(
            action_id=action_id,
            action_name="test_action",
            node_id=node_id,
            node_name="test_node",
            description="Test description",
            deprecated=True,
            category=EnumActionCategory.VALIDATION,
        )

        data = action.model_dump()

        expected_data = {
            "action_id": action_id,
            "action_name": "test_action",
            "node_id": node_id,
            "node_name": "test_node",
            "description": "Test description",
            "deprecated": True,
            "category": "validation",
        }

        assert data == expected_data

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        node_id = uuid4()
        action_id = uuid4()
        data = {
            "action_id": str(action_id),
            "action_name": "restore",
            "node_id": str(node_id),
            "node_name": "backup_node",
            "description": "Restore from backup",
            "deprecated": False,
            "category": "system",
        }

        action = ModelCliAction.model_validate(data)

        assert action.action_id == action_id
        assert action.action_name == "restore"
        assert action.node_id == node_id
        assert action.node_name == "backup_node"
        assert action.description == "Restore from backup"
        assert action.deprecated is False
        assert action.category == EnumActionCategory.SYSTEM

    def test_model_json_serialization(self):
        """Test JSON serialization and deserialization."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="backup",
            node_id=node_id,
            node_name="data_node",
            description="Backup data",
        )

        # Serialize to JSON
        json_str = action.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        action_from_json = ModelCliAction.model_validate_json(json_str)

        assert action_from_json.action_id == action.action_id
        assert action_from_json.action_name == action.action_name
        assert action_from_json.node_id == action.node_id
        assert action_from_json.node_name == action.node_name
        assert action_from_json.description == action.description
        assert action_from_json.deprecated == action.deprecated
        assert action_from_json.category == action.category

    def test_model_equality(self):
        """Test model equality comparison."""
        node_id = uuid4()
        action_id = uuid4()

        action1 = ModelCliAction(
            action_id=action_id,
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        action2 = ModelCliAction(
            action_id=action_id,
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        action3 = ModelCliAction(
            action_name="configure",
            node_id=node_id,
            node_name="app_node",
            description="Configure application",
        )

        assert action1 == action2
        assert action1 != action3  # Different action_id (auto-generated)

    def test_model_repr(self):
        """Test model string representation."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="deploy",
            node_id=node_id,
            node_name="app_node",
            description="Deploy application",
        )

        repr_str = repr(action)
        assert "ModelCliAction" in repr_str
        assert "deploy" in repr_str
        assert "app_node" in repr_str

    def test_optional_fields_defaults(self):
        """Test that optional fields have correct defaults."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="test_node",
            description="Test description",
        )

        assert action.deprecated is False
        assert action.category is None
        assert isinstance(action.action_id, UUID)  # Auto-generated

    def test_category_field_accepts_none_and_enum_values(self):
        """Test that category field accepts None and enum values."""
        node_id = uuid4()

        # Test with None (default)
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="test_node",
            description="Test description",
        )
        assert action.category is None

        # Test with enum value
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="test_node",
            description="Test description",
            category=EnumActionCategory.CONFIGURATION,
        )
        assert action.category == EnumActionCategory.CONFIGURATION

        # Test with invalid string should fail
        with pytest.raises(ValidationError):
            ModelCliAction(
                action_name="test_action",
                node_id=node_id,
                node_name="test_node",
                description="Test description",
                category="invalid_category",
            )


class TestModelCliActionEdgeCases:
    """Test edge cases and error conditions for ModelCliAction."""

    def test_empty_string_fields(self):
        """Test behavior with empty string fields."""
        node_id = uuid4()

        # Empty action_name should fail pattern validation
        with pytest.raises(ValidationError):
            ModelCliAction(
                action_name="",
                node_id=node_id,
                node_name="test_node",
                description="Test description",
            )

        # Empty node_name is currently allowed by the model
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="",
            description="Test description",
        )
        assert action.node_name == ""

        # Empty description is currently allowed by the model
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="test_node",
            description="",
        )
        assert action.description == ""

    def test_whitespace_handling(self):
        """Test handling of whitespace in fields."""
        # Test that leading/trailing whitespace is preserved
        node_id = uuid4()
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name=" test_node ",
            description=" Test description ",
        )

        assert action.node_name == " test_node "
        assert action.description == " Test description "

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="test_node_ñ",
            description="Test description with émojis 🚀",
        )

        assert action.node_name == "test_node_ñ"
        assert action.description == "Test description with émojis 🚀"

    def test_very_long_strings(self):
        """Test handling of very long strings."""
        long_string = "a" * 1000
        node_id = uuid4()

        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name=long_string,
            description=long_string,
        )

        assert len(action.node_name) == 1000
        assert len(action.description) == 1000

    def test_special_characters_in_allowed_fields(self):
        """Test special characters in fields that allow them."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="node-with-special@chars!",
            description="Description with all sorts of characters: @#$%^&*()[]{}|\\:;\"'<>?,./",
        )

        assert "special@chars!" in action.node_name
        assert "@#$%^&*()" in action.description

    def test_none_values_for_optional_fields(self):
        """Test explicit None values for optional fields."""
        node_id = uuid4()
        action = ModelCliAction(
            action_name="test_action",
            node_id=node_id,
            node_name="test_node",
            description="Test description",
            category=None,
        )

        assert action.category is None

    def test_factory_method_with_invalid_pattern(self):
        """Test factory method with invalid action_name pattern."""
        node_id = uuid4()
        with pytest.raises(ValidationError):
            ModelCliAction.from_contract_action(
                action_name="Invalid-Action", node_id=node_id, node_name="test_node"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
