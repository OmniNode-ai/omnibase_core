"""
Test CLI Node Execution Input Model functionality.

Validates that the ModelCliNodeExecutionInput works correctly with
parameter handling, legacy compatibility, and validation.
"""

import pytest
from typing import Dict, Any

from omnibase_core.models.nodes import ModelCliNodeExecutionInput


class TestCliNodeExecutionInput:
    """Test ModelCliNodeExecutionInput functionality."""

    def test_basic_creation_with_required_fields(self):
        """Test basic creation with only required fields."""
        cli_input = ModelCliNodeExecutionInput(action="test_action")

        assert cli_input.action == "test_action"
        assert cli_input.node_name is None
        assert cli_input.include_metadata is True
        assert cli_input.include_health_info is True
        assert cli_input.health_filter is True
        assert cli_input.output_format == "default"
        assert not cli_input.verbose

    def test_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        cli_input = ModelCliNodeExecutionInput(
            action="list_nodes",
            node_name="test_node",
            target_node="target_test",
            include_metadata=False,
            include_health_info=False,
            health_filter=False,
            category_filter="generation",
            timeout_seconds=60.0,
            output_format="json",
            verbose=True,
            execution_context="test_context",
            request_id="req_12345",
        )

        assert cli_input.action == "list_nodes"
        assert cli_input.node_name == "test_node"
        assert cli_input.target_node == "target_test"
        assert not cli_input.include_metadata
        assert not cli_input.include_health_info
        assert not cli_input.health_filter
        assert cli_input.category_filter == "generation"
        assert cli_input.timeout_seconds == 60.0
        assert cli_input.output_format == "json"
        assert cli_input.verbose
        assert cli_input.execution_context == "test_context"
        assert cli_input.request_id == "req_12345"

    def test_to_legacy_dict_basic(self):
        """Test conversion to legacy dictionary format."""
        cli_input = ModelCliNodeExecutionInput(
            action="test_action",
            include_metadata=True,
            health_filter=False,
            verbose=True,
        )

        legacy_dict = cli_input.to_legacy_dict()

        assert legacy_dict["action"] == "test_action"
        assert legacy_dict["include_metadata"] is True
        assert legacy_dict["health_filter"] is False
        assert legacy_dict["verbose"] is True
        assert legacy_dict["output_format"] == "default"

    def test_to_legacy_dict_with_optional_fields(self):
        """Test legacy dict conversion with optional fields."""
        cli_input = ModelCliNodeExecutionInput(
            action="node_info",
            node_name="specific_node",
            target_node="target_node",
            category_filter="validation",
            execution_context="cli_test",
            request_id="req_789",
            timeout_seconds=30.0,
        )

        legacy_dict = cli_input.to_legacy_dict()

        assert legacy_dict["action"] == "node_info"
        assert legacy_dict["node_name"] == "specific_node"
        assert legacy_dict["target_node"] == "target_node"
        assert legacy_dict["category_filter"] == "validation"
        assert legacy_dict["execution_context"] == "cli_test"
        assert legacy_dict["request_id"] == "req_789"
        assert legacy_dict["timeout_seconds"] == 30.0

    def test_to_legacy_dict_excludes_none_values(self):
        """Test that None values are excluded from legacy dict."""
        cli_input = ModelCliNodeExecutionInput(
            action="test_action",
            node_name=None,
            target_node=None,
            category_filter=None,
        )

        legacy_dict = cli_input.to_legacy_dict()

        assert "node_name" not in legacy_dict
        assert "target_node" not in legacy_dict
        assert "category_filter" not in legacy_dict
        assert "execution_context" not in legacy_dict
        assert "request_id" not in legacy_dict

    def test_from_legacy_dict_basic(self):
        """Test creation from legacy dictionary format."""
        legacy_data = {
            "action": "list_nodes",
            "include_metadata": False,
            "health_filter": True,
            "verbose": False,
        }

        cli_input = ModelCliNodeExecutionInput.from_legacy_dict(legacy_data)

        assert cli_input.action == "list_nodes"
        assert not cli_input.include_metadata
        assert cli_input.health_filter
        assert not cli_input.verbose

    def test_from_legacy_dict_with_all_fields(self):
        """Test from_legacy_dict with all possible fields."""
        legacy_data = {
            "action": "node_info",
            "node_name": "test_node",
            "target_node": "target_test",
            "include_metadata": True,
            "include_health_info": False,
            "health_filter": False,
            "category_filter": "generation",
            "timeout_seconds": 45.0,
            "output_format": "table",
            "verbose": True,
            "execution_context": "legacy_test",
            "request_id": "legacy_req_123",
        }

        cli_input = ModelCliNodeExecutionInput.from_legacy_dict(legacy_data)

        assert cli_input.action == "node_info"
        assert cli_input.node_name == "test_node"
        assert cli_input.target_node == "target_test"
        assert cli_input.include_metadata
        assert not cli_input.include_health_info
        assert not cli_input.health_filter
        assert cli_input.category_filter == "generation"
        assert cli_input.timeout_seconds == 45.0
        assert cli_input.output_format == "table"
        assert cli_input.verbose
        assert cli_input.execution_context == "legacy_test"
        assert cli_input.request_id == "legacy_req_123"

    def test_from_legacy_dict_with_advanced_params(self):
        """Test from_legacy_dict with advanced parameters."""
        legacy_data = {
            "action": "complex_action",
            "include_metadata": True,
            # Advanced parameters
            "custom_param1": "value1",
            "custom_param2": 42,
            "custom_flag": True,
        }

        cli_input = ModelCliNodeExecutionInput.from_legacy_dict(legacy_data)

        assert cli_input.action == "complex_action"
        assert cli_input.include_metadata

        # Advanced params should be in the advanced_params object
        advanced_dict = cli_input.advanced_params.to_dict()
        assert "custom_param1" in advanced_dict
        assert "custom_param2" in advanced_dict
        assert "custom_flag" in advanced_dict

    def test_roundtrip_legacy_conversion(self):
        """Test roundtrip conversion: model -> dict -> model."""
        original = ModelCliNodeExecutionInput(
            action="roundtrip_test",
            node_name="test_node",
            include_metadata=False,
            timeout_seconds=20.0,
            verbose=True,
            execution_context="roundtrip_context",
        )

        # Convert to legacy dict
        legacy_dict = original.to_legacy_dict()

        # Convert back to model
        restored = ModelCliNodeExecutionInput.from_legacy_dict(legacy_dict)

        # Should be equivalent
        assert restored.action == original.action
        assert restored.node_name == original.node_name
        assert restored.include_metadata == original.include_metadata
        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.verbose == original.verbose
        assert restored.execution_context == original.execution_context

    def test_output_format_validation(self):
        """Test output format options."""
        valid_formats = ["default", "json", "table"]

        for format_type in valid_formats:
            cli_input = ModelCliNodeExecutionInput(
                action="test",
                output_format=format_type,
            )
            assert cli_input.output_format == format_type

    def test_timeout_handling(self):
        """Test timeout parameter handling."""
        # No timeout specified
        cli_input = ModelCliNodeExecutionInput(action="test")
        assert cli_input.timeout_seconds is None

        # Specific timeout
        cli_input = ModelCliNodeExecutionInput(
            action="test",
            timeout_seconds=120.5,
        )
        assert cli_input.timeout_seconds == 120.5

    def test_boolean_flag_handling(self):
        """Test boolean flag handling."""
        cli_input = ModelCliNodeExecutionInput(
            action="test",
            include_metadata=False,
            include_health_info=False,
            health_filter=False,
            verbose=True,
        )

        assert not cli_input.include_metadata
        assert not cli_input.include_health_info
        assert not cli_input.health_filter
        assert cli_input.verbose

    def test_advanced_params_integration(self):
        """Test advanced parameters integration."""
        cli_input = ModelCliNodeExecutionInput(action="test")

        # Should have default advanced params
        assert cli_input.advanced_params is not None

        # Should be able to convert to dict
        advanced_dict = cli_input.advanced_params.to_dict()
        assert isinstance(advanced_dict, dict)

    def test_model_serialization(self):
        """Test Pydantic model serialization."""
        cli_input = ModelCliNodeExecutionInput(
            action="serialize_test",
            node_name="test_node",
            verbose=True,
            timeout_seconds=30.0,
        )

        # Serialize
        serialized = cli_input.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["action"] == "serialize_test"

        # Deserialize
        restored = ModelCliNodeExecutionInput.model_validate(serialized)
        assert restored.action == cli_input.action
        assert restored.node_name == cli_input.node_name
        assert restored.verbose == cli_input.verbose
        assert restored.timeout_seconds == cli_input.timeout_seconds

    def test_config_example_schema(self):
        """Test that the config example schema is valid."""
        # The example in Config should be valid
        example_data = {
            "action": "list_nodes",
            "node_name": None,
            "target_node": None,
            "include_metadata": True,
            "include_health_info": True,
            "health_filter": True,
            "category_filter": None,
            "timeout_seconds": 30.0,
            "output_format": "default",
            "verbose": False,
            "advanced_params": {},
            "execution_context": "cli_main",
            "request_id": "req_123456",
        }

        # Should create valid instance
        cli_input = ModelCliNodeExecutionInput.model_validate(example_data)
        assert cli_input.action == "list_nodes"

    def test_validation_errors(self):
        """Test validation error handling."""
        # Missing required action
        with pytest.raises(Exception):
            ModelCliNodeExecutionInput()

        # Empty action
        with pytest.raises(Exception):
            ModelCliNodeExecutionInput(action="")

    def test_default_values(self):
        """Test default values are set correctly."""
        cli_input = ModelCliNodeExecutionInput(action="test")

        # Test all defaults
        assert cli_input.node_name is None
        assert cli_input.target_node is None
        assert cli_input.include_metadata is True
        assert cli_input.include_health_info is True
        assert cli_input.health_filter is True
        assert cli_input.category_filter is None
        assert cli_input.timeout_seconds is None
        assert cli_input.output_format == "default"
        assert cli_input.verbose is False
        assert cli_input.execution_context is None
        assert cli_input.request_id is None

    def test_specific_action_patterns(self):
        """Test patterns for specific action types."""
        # List nodes action
        list_input = ModelCliNodeExecutionInput(
            action="list_nodes",
            include_metadata=True,
            health_filter=True,
        )
        assert list_input.action == "list_nodes"

        # Node info action
        info_input = ModelCliNodeExecutionInput(
            action="node_info",
            target_node="specific_node",
            include_health_info=True,
        )
        assert info_input.action == "node_info"
        assert info_input.target_node == "specific_node"

        # Run node action
        run_input = ModelCliNodeExecutionInput(
            action="run_node",
            node_name="CONTRACT_TO_MODEL",
            timeout_seconds=60.0,
            verbose=True,
        )
        assert run_input.action == "run_node"
        assert run_input.node_name == "CONTRACT_TO_MODEL"

    def test_category_filter_functionality(self):
        """Test category filter functionality."""
        categories = ["generation", "validation", "template", "runtime"]

        for category in categories:
            cli_input = ModelCliNodeExecutionInput(
                action="list_nodes",
                category_filter=category,
            )
            assert cli_input.category_filter == category

    def test_execution_context_tracking(self):
        """Test execution context tracking."""
        contexts = ["cli_main", "test_suite", "batch_operation", "interactive"]

        for context in contexts:
            cli_input = ModelCliNodeExecutionInput(
                action="test",
                execution_context=context,
            )
            assert cli_input.execution_context == context

    def test_request_id_tracking(self):
        """Test request ID tracking."""
        cli_input = ModelCliNodeExecutionInput(
            action="test",
            request_id="req_unique_12345",
        )
        assert cli_input.request_id == "req_unique_12345"

    @pytest.mark.parametrize("action", [
        "list_nodes",
        "node_info",
        "run_node",
        "validate_contracts",
        "generate_models",
        "create_files",
    ])
    def test_common_action_types(self, action):
        """Test common action types work correctly."""
        cli_input = ModelCliNodeExecutionInput(action=action)
        assert cli_input.action == action

        # Should serialize correctly
        serialized = cli_input.model_dump()
        assert serialized["action"] == action

        # Should convert to legacy format
        legacy_dict = cli_input.to_legacy_dict()
        assert legacy_dict["action"] == action

    def test_performance_with_large_advanced_params(self):
        """Test performance with large advanced parameters."""
        # Create large legacy dict
        large_legacy_data = {
            "action": "complex_operation",
            "include_metadata": True,
        }

        # Add many advanced parameters
        for i in range(100):
            large_legacy_data[f"param_{i}"] = f"value_{i}"

        # Should handle efficiently
        cli_input = ModelCliNodeExecutionInput.from_legacy_dict(large_legacy_data)
        assert cli_input.action == "complex_operation"

        # Advanced params should contain all extra parameters
        advanced_dict = cli_input.advanced_params.to_dict()
        assert len(advanced_dict) == 100

        # Should convert back efficiently
        legacy_dict = cli_input.to_legacy_dict()
        assert len(legacy_dict) >= 100