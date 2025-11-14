"""
Tests for ModelWorkflowInput.

Tests the workflow input model for individual workflow input definitions.
"""

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.configuration.model_workflow_input import ModelWorkflowInput


class TestModelWorkflowInput:
    """Test class for ModelWorkflowInput."""

    def test_model_initialization(self):
        """Test model can be instantiated."""
        workflow_input = ModelWorkflowInput(
            description="Test input",
            required=True,
            default="default_value",
            type="string",
            options=["option1", "option2"],
        )
        assert workflow_input is not None

    def test_model_inheritance(self):
        """Test model inheritance."""
        assert issubclass(ModelWorkflowInput, BaseModel)

    def test_model_with_minimal_fields(self):
        """Test model with minimal required fields."""
        workflow_input = ModelWorkflowInput(description="Test input")

        assert workflow_input.description == "Test input"
        assert workflow_input.required is False  # Default value
        assert workflow_input.default is None  # Default value
        assert workflow_input.type == "string"  # Default value
        assert workflow_input.options is None  # Default value

    def test_model_with_all_fields(self):
        """Test model with all fields."""
        workflow_input = ModelWorkflowInput(
            description="Test input description",
            required=True,
            default="test_default",
            type="choice",
            options=["option1", "option2", "option3"],
        )

        assert workflow_input.description == "Test input description"
        assert workflow_input.required is True
        assert workflow_input.default == "test_default"
        assert workflow_input.type == "choice"
        assert workflow_input.options == ["option1", "option2", "option3"]

    def test_model_required_field_validation(self):
        """Test that description is required."""
        with pytest.raises(ValidationError):
            ModelWorkflowInput()

    def test_model_boolean_required_field(self):
        """Test boolean required field."""
        workflow_input = ModelWorkflowInput(description="Test", required=True)
        assert workflow_input.required is True

        workflow_input = ModelWorkflowInput(description="Test", required=False)
        assert workflow_input.required is False

    def test_model_default_value_types(self):
        """Test different default value types."""
        # String default
        workflow_input = ModelWorkflowInput(description="Test", default="string_value")
        assert workflow_input.default == "string_value"

        # Integer default
        workflow_input = ModelWorkflowInput(description="Test", default=42)
        assert workflow_input.default == 42

        # Boolean default
        workflow_input = ModelWorkflowInput(description="Test", default=True)
        assert workflow_input.default is True

        # List default
        workflow_input = ModelWorkflowInput(
            description="Test", default=["item1", "item2"]
        )
        assert workflow_input.default == ["item1", "item2"]

        # Dict default
        workflow_input = ModelWorkflowInput(
            description="Test", default={"key": "value"}
        )
        assert workflow_input.default == {"key": "value"}

    def test_model_type_field_values(self):
        """Test different type field values."""
        # String type
        workflow_input = ModelWorkflowInput(description="Test", type="string")
        assert workflow_input.type == "string"

        # Choice type
        workflow_input = ModelWorkflowInput(description="Test", type="choice")
        assert workflow_input.type == "choice"

        # Boolean type
        workflow_input = ModelWorkflowInput(description="Test", type="boolean")
        assert workflow_input.type == "boolean"

        # Custom type
        workflow_input = ModelWorkflowInput(description="Test", type="custom_type")
        assert workflow_input.type == "custom_type"

    def test_model_options_field(self):
        """Test options field."""
        # With options
        options = ["option1", "option2", "option3"]
        workflow_input = ModelWorkflowInput(description="Test", options=options)
        assert workflow_input.options == options

        # Without options (None)
        workflow_input = ModelWorkflowInput(description="Test", options=None)
        assert workflow_input.options is None

        # Empty options list
        workflow_input = ModelWorkflowInput(description="Test", options=[])
        assert workflow_input.options == []

    def test_model_serialization(self):
        """Test model serialization."""
        workflow_input = ModelWorkflowInput(
            description="Test input",
            required=True,
            default="test_default",
            type="choice",
            options=["option1", "option2"],
        )

        data = workflow_input.model_dump()
        assert isinstance(data, dict)
        assert data["description"] == "Test input"
        assert data["required"] is True
        assert data["default"] == "test_default"
        assert data["type"] == "choice"
        assert data["options"] == ["option1", "option2"]

    def test_model_deserialization(self):
        """Test model deserialization."""
        data = {
            "description": "Test input",
            "required": True,
            "default": "test_default",
            "type": "choice",
            "options": ["option1", "option2"],
        }

        workflow_input = ModelWorkflowInput.model_validate(data)
        assert workflow_input.description == "Test input"
        assert workflow_input.required is True
        assert workflow_input.default == "test_default"
        assert workflow_input.type == "choice"
        assert workflow_input.options == ["option1", "option2"]

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        workflow_input = ModelWorkflowInput(
            description="Test input", required=True, default="test_default"
        )

        json_data = workflow_input.model_dump_json()
        assert isinstance(json_data, str)
        assert "Test input" in json_data
        assert "test_default" in json_data

    def test_model_roundtrip(self):
        """Test model roundtrip serialization."""
        original = ModelWorkflowInput(
            description="Test input",
            required=True,
            default="test_default",
            type="choice",
            options=["option1", "option2"],
        )

        data = original.model_dump()
        restored = ModelWorkflowInput.model_validate(data)

        assert restored.model_dump() == original.model_dump()

    def test_model_equality(self):
        """Test model equality."""
        workflow_input1 = ModelWorkflowInput(
            description="Test input", required=True, default="test_default"
        )
        workflow_input2 = ModelWorkflowInput(
            description="Test input", required=True, default="test_default"
        )

        assert workflow_input1.model_dump() == workflow_input2.model_dump()

    def test_model_str_representation(self):
        """Test model string representation."""
        workflow_input = ModelWorkflowInput(description="Test input")
        str_repr = str(workflow_input)
        assert isinstance(str_repr, str)
        assert "description" in str_repr

    def test_model_repr(self):
        """Test model repr."""
        workflow_input = ModelWorkflowInput(description="Test input")
        repr_str = repr(workflow_input)
        assert isinstance(repr_str, str)
        assert "ModelWorkflowInput" in repr_str

    def test_model_attributes(self):
        """Test model attributes."""
        workflow_input = ModelWorkflowInput(description="Test input")

        # Test that model has expected attributes
        assert hasattr(workflow_input, "description")
        assert hasattr(workflow_input, "required")
        assert hasattr(workflow_input, "default")
        assert hasattr(workflow_input, "type")
        assert hasattr(workflow_input, "options")
        assert hasattr(workflow_input, "model_dump")
        assert hasattr(workflow_input, "model_validate")

    def test_model_validation(self):
        """Test model validation."""
        # Test with valid data
        workflow_input = ModelWorkflowInput.model_validate(
            {
                "description": "Test input",
                "required": True,
                "default": "test_default",
                "type": "string",
                "options": None,
            }
        )
        assert isinstance(workflow_input, ModelWorkflowInput)

    def test_model_metadata(self):
        """Test model metadata."""
        workflow_input = ModelWorkflowInput(description="Test input")
        assert hasattr(workflow_input, "__class__")
        assert workflow_input.__class__.__name__ == "ModelWorkflowInput"

    def test_model_creation_with_data(self):
        """Test model creation with data."""
        data = {
            "description": "Test input",
            "required": False,
            "default": None,
            "type": "boolean",
            "options": None,
        }
        workflow_input = ModelWorkflowInput.model_validate(data)
        assert workflow_input.model_dump() == data

    def test_model_copy(self):
        """Test model copying."""
        workflow_input = ModelWorkflowInput(
            description="Test input", required=True, default="test_default"
        )
        copied = workflow_input.model_copy()
        assert copied.model_dump() == workflow_input.model_dump()
        assert copied is not workflow_input  # Different instances

    def test_model_immutability(self):
        """Test model immutability."""
        workflow_input = ModelWorkflowInput(description="Test input")
        # Test that model fields cannot be modified after creation
        # (depends on model configuration)

    def test_model_field_descriptions(self):
        """Test model field descriptions."""
        fields = ModelWorkflowInput.model_fields

        assert "description" in fields
        assert "required" in fields
        assert "default" in fields
        assert "type" in fields
        assert "options" in fields

        # Check field descriptions
        assert "Input description" in fields["description"].description
        assert "Whether input is required" in fields["required"].description
        assert "Default value" in fields["default"].description
        assert "Input type" in fields["type"].description
        assert "Options for choice type" in fields["options"].description

    def test_model_default_factories(self):
        """Test model default factories."""
        # Test that default values are applied correctly
        workflow_input = ModelWorkflowInput(description="Test input")

        assert workflow_input.required is False  # Default factory
        assert workflow_input.default is None  # Default factory
        assert workflow_input.type == "string"  # Default factory
        assert workflow_input.options is None  # Default factory
