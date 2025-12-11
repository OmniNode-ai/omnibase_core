"""
Unit tests for ModelFSMOperation.

Tests all aspects of the reserved FSM operation model including:
- Model instantiation and validation
- Required and optional fields
- Protocol implementations (execute, serialize, validate)
- Serialization and deserialization
- Edge cases and error conditions

Note:
    This tests a RESERVED model for v1.1+ functionality.
    See CONTRACT_DRIVEN_NODEREDUCER_V1_0.md for specification.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.fsm.model_fsm_operation import ModelFSMOperation


class TestModelFSMOperationInstantiation:
    """Test cases for ModelFSMOperation instantiation."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with required fields only."""
        operation = ModelFSMOperation(
            operation_name="validate_input",
            operation_type="synchronous",
        )

        assert operation.operation_name == "validate_input"
        assert operation.operation_type == "synchronous"
        assert operation.description is None

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields populated."""
        operation = ModelFSMOperation(
            operation_name="process_data",
            operation_type="asynchronous",
            description="Processes incoming data asynchronously",
        )

        assert operation.operation_name == "process_data"
        assert operation.operation_type == "asynchronous"
        assert operation.description == "Processes incoming data asynchronously"

    def test_model_instantiation_with_empty_description(self):
        """Test model instantiation with empty string description."""
        operation = ModelFSMOperation(
            operation_name="cleanup",
            operation_type="batch",
            description="",
        )

        assert operation.operation_name == "cleanup"
        assert operation.operation_type == "batch"
        assert operation.description == ""


class TestModelFSMOperationDefaultValues:
    """Test default value handling for ModelFSMOperation."""

    def test_description_defaults_to_none(self):
        """Test that description defaults to None when not provided."""
        operation = ModelFSMOperation(
            operation_name="test_op",
            operation_type="sync",
        )

        assert operation.description is None

    def test_required_fields_have_no_defaults(self):
        """Test that required fields raise error when missing."""
        # Missing operation_name
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMOperation(operation_type="sync")
        assert "operation_name" in str(exc_info.value)

        # Missing operation_type
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMOperation(operation_name="test")
        assert "operation_type" in str(exc_info.value)

        # Missing both required fields
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMOperation()
        error_str = str(exc_info.value)
        assert "operation_name" in error_str
        assert "operation_type" in error_str


class TestModelFSMOperationValidation:
    """Test validation rules for ModelFSMOperation."""

    def test_operation_name_type_validation(self):
        """Test that operation_name must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name=123, operation_type="sync")

        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name=None, operation_type="sync")

        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name=["name"], operation_type="sync")

        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name={"name": "value"}, operation_type="sync")

    def test_operation_type_type_validation(self):
        """Test that operation_type must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name="test", operation_type=123)

        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name="test", operation_type=None)

        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name="test", operation_type=["type"])

        with pytest.raises(ValidationError):
            ModelFSMOperation(operation_name="test", operation_type={"type": "val"})

    def test_description_type_validation(self):
        """Test that description must be a string or None."""
        # Valid: string
        op1 = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
            description="Valid description",
        )
        assert op1.description == "Valid description"

        # Valid: None (explicit)
        op2 = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
            description=None,
        )
        assert op2.description is None

        # Invalid: non-string types
        with pytest.raises(ValidationError):
            ModelFSMOperation(
                operation_name="test",
                operation_type="sync",
                description=123,
            )

        with pytest.raises(ValidationError):
            ModelFSMOperation(
                operation_name="test",
                operation_type="sync",
                description=["desc"],
            )


class TestModelFSMOperationProtocols:
    """Test protocol implementations for ModelFSMOperation."""

    def test_execute_protocol_basic(self):
        """Test execute protocol method returns True."""
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
        )

        result = operation.execute()
        assert result is True

    def test_execute_protocol_with_updates(self):
        """Test execute protocol with field updates."""
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
            description="original",
        )

        result = operation.execute(description="updated description")
        assert result is True
        assert operation.description == "updated description"

    def test_execute_protocol_with_invalid_field(self):
        """Test execute protocol ignores non-existent fields."""
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
        )

        # Non-existent field should be ignored
        result = operation.execute(nonexistent_field="value")
        assert result is True
        assert not hasattr(operation, "nonexistent_field")

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        operation = ModelFSMOperation(
            operation_name="serialize_test",
            operation_type="batch",
            description="Test serialization",
        )

        serialized = operation.serialize()

        assert isinstance(serialized, dict)
        assert serialized["operation_name"] == "serialize_test"
        assert serialized["operation_type"] == "batch"
        assert serialized["description"] == "Test serialization"

    def test_serialize_protocol_with_none_description(self):
        """Test serialize protocol with None description."""
        operation = ModelFSMOperation(
            operation_name="minimal",
            operation_type="sync",
        )

        serialized = operation.serialize()

        assert isinstance(serialized, dict)
        assert serialized["operation_name"] == "minimal"
        assert serialized["operation_type"] == "sync"
        assert serialized["description"] is None

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
        )

        result = operation.validate_instance()
        assert result is True

    def test_validate_instance_protocol_full(self):
        """Test validate_instance with all fields populated."""
        operation = ModelFSMOperation(
            operation_name="full_test",
            operation_type="asynchronous",
            description="Full operation description",
        )

        result = operation.validate_instance()
        assert result is True


class TestModelFSMOperationSerialization:
    """Test serialization and deserialization for ModelFSMOperation."""

    def test_model_dump(self):
        """Test model_dump method."""
        operation = ModelFSMOperation(
            operation_name="dump_test",
            operation_type="sync",
            description="Dump test description",
        )

        data = operation.model_dump()

        assert isinstance(data, dict)
        assert data["operation_name"] == "dump_test"
        assert data["operation_type"] == "sync"
        assert data["description"] == "Dump test description"

    def test_model_validate(self):
        """Test model_validate method."""
        data = {
            "operation_name": "validated_op",
            "operation_type": "batch",
            "description": "Validated operation",
        }

        operation = ModelFSMOperation.model_validate(data)

        assert operation.operation_name == "validated_op"
        assert operation.operation_type == "batch"
        assert operation.description == "Validated operation"

    def test_model_validate_minimal(self):
        """Test model_validate with minimal data."""
        data = {
            "operation_name": "minimal_op",
            "operation_type": "sync",
        }

        operation = ModelFSMOperation.model_validate(data)

        assert operation.operation_name == "minimal_op"
        assert operation.operation_type == "sync"
        assert operation.description is None

    def test_model_dump_json(self):
        """Test JSON serialization."""
        operation = ModelFSMOperation(
            operation_name="json_test",
            operation_type="async",
            description="JSON test",
        )

        json_str = operation.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert "async" in json_str
        assert "JSON test" in json_str

    def test_model_validate_json(self):
        """Test JSON deserialization."""
        json_str = '{"operation_name": "from_json", "operation_type": "batch", "description": "From JSON"}'

        operation = ModelFSMOperation.model_validate_json(json_str)

        assert operation.operation_name == "from_json"
        assert operation.operation_type == "batch"
        assert operation.description == "From JSON"

    def test_model_validate_json_minimal(self):
        """Test JSON deserialization with minimal fields."""
        json_str = '{"operation_name": "minimal_json", "operation_type": "sync"}'

        operation = ModelFSMOperation.model_validate_json(json_str)

        assert operation.operation_name == "minimal_json"
        assert operation.operation_type == "sync"
        assert operation.description is None

    def test_roundtrip_serialization(self):
        """Test roundtrip serialization and deserialization."""
        original = ModelFSMOperation(
            operation_name="roundtrip",
            operation_type="async",
            description="Roundtrip test",
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        restored = ModelFSMOperation.model_validate_json(json_str)

        assert restored.operation_name == original.operation_name
        assert restored.operation_type == original.operation_type
        assert restored.description == original.description


class TestModelFSMOperationEdgeCases:
    """Test edge cases for ModelFSMOperation."""

    def test_empty_string_operation_name(self):
        """Test operation with empty string name."""
        operation = ModelFSMOperation(
            operation_name="",
            operation_type="sync",
        )
        assert operation.operation_name == ""

    def test_empty_string_operation_type(self):
        """Test operation with empty string type."""
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="",
        )
        assert operation.operation_type == ""

    def test_very_long_operation_name(self):
        """Test operation with very long name."""
        long_name = "operation_" + "x" * 10000
        operation = ModelFSMOperation(
            operation_name=long_name,
            operation_type="sync",
        )
        assert len(operation.operation_name) > 10000

    def test_very_long_description(self):
        """Test operation with very long description."""
        long_desc = "Description: " + "y" * 50000
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
            description=long_desc,
        )
        assert len(operation.description) > 50000

    def test_operation_name_with_special_characters(self):
        """Test operation names with special characters."""
        special_names = [
            "operation-with-dashes",
            "operation_with_underscores",
            "operation.with.dots",
            "operation:with:colons",
            "operation/with/slashes",
            "operation with spaces",
            "opération-français",
            "操作-日本語",
            "operation@with#symbols$",
        ]

        for name in special_names:
            operation = ModelFSMOperation(
                operation_name=name,
                operation_type="sync",
            )
            assert operation.operation_name == name

    def test_operation_type_with_special_characters(self):
        """Test operation types with special characters."""
        special_types = [
            "sync-async-hybrid",
            "type_with_underscore",
            "type.namespaced",
            "type:variant",
        ]

        for op_type in special_types:
            operation = ModelFSMOperation(
                operation_name="test",
                operation_type=op_type,
            )
            assert operation.operation_type == op_type

    def test_model_equality(self):
        """Test model equality comparison."""
        op1 = ModelFSMOperation(
            operation_name="equal",
            operation_type="sync",
            description="Same",
        )
        op2 = ModelFSMOperation(
            operation_name="equal",
            operation_type="sync",
            description="Same",
        )
        op3 = ModelFSMOperation(
            operation_name="different",
            operation_type="sync",
            description="Same",
        )

        assert op1 == op2
        assert op1 != op3

    def test_model_equality_with_none_description(self):
        """Test model equality when description is None."""
        op1 = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
        )
        op2 = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
            description=None,
        )

        assert op1 == op2

    def test_validate_assignment_config(self):
        """Test that validate_assignment config works."""
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
        )

        # Should allow valid assignment
        operation.description = "updated"
        assert operation.description == "updated"

        # Invalid assignment should raise error
        with pytest.raises(ValidationError):
            operation.operation_name = 123

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per config."""
        data = {
            "operation_name": "test",
            "operation_type": "sync",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        operation = ModelFSMOperation.model_validate(data)
        assert operation.operation_name == "test"
        assert not hasattr(operation, "extra_field")
        assert not hasattr(operation, "another_extra")

    def test_whitespace_in_fields(self):
        """Test handling of whitespace in field values."""
        operation = ModelFSMOperation(
            operation_name="  spaced_name  ",
            operation_type="\ttabbed_type\t",
            description="  description with whitespace  ",
        )

        # Whitespace should be preserved (no automatic stripping)
        assert operation.operation_name == "  spaced_name  "
        assert operation.operation_type == "\ttabbed_type\t"
        assert operation.description == "  description with whitespace  "

    def test_newlines_in_description(self):
        """Test handling of newlines in description."""
        multiline_desc = """Line 1
Line 2
Line 3"""
        operation = ModelFSMOperation(
            operation_name="test",
            operation_type="sync",
            description=multiline_desc,
        )

        assert "\n" in operation.description
        assert "Line 1" in operation.description
        assert "Line 3" in operation.description


class TestModelFSMOperationReservedForV11:
    """Tests verifying the model's reserved status for v1.1+."""

    def test_docstring_contains_reserved_notice(self):
        """Test that the model docstring mentions v1.1+ reservation."""
        docstring = ModelFSMOperation.__doc__
        assert docstring is not None
        assert "v1.1" in docstring or "1.1" in docstring
        assert "reserved" in docstring.lower() or "RESERVED" in docstring

    def test_module_docstring_contains_spec_reference(self):
        """Test that the module contains spec reference."""
        import omnibase_core.models.fsm.model_fsm_operation as module

        module_doc = module.__doc__
        assert module_doc is not None
        assert (
            "CONTRACT_DRIVEN_NODEREDUCER" in module_doc
            or "Spec Reference" in module_doc
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
