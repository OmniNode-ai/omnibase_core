"""
Unit tests for ModelFunctionNode.

Tests all aspects of the function node model including:
- Model instantiation and validation
- Composed sub-models (core, metadata, performance)
- Property delegations
- TODO stub implementations (NotImplementedError)
- Factory methods
- Protocol implementations
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_function_type import EnumFunctionType
from omnibase_core.enums.enum_operational_complexity import EnumOperationalComplexity
from omnibase_core.enums.enum_return_type import EnumReturnType
from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.nodes.model_function_node import ModelFunctionNode
from omnibase_core.models.nodes.model_function_node_core import ModelFunctionNodeCore
from omnibase_core.models.nodes.model_function_node_metadata import (
    ModelFunctionNodeMetadata,
)
from omnibase_core.models.nodes.model_function_node_performance import (
    ModelFunctionNodePerformance,
)


class TestModelFunctionNode:
    """Test cases for ModelFunctionNode."""

    def test_model_instantiation_with_core(self):
        """Test that model can be instantiated with core info."""
        core = ModelFunctionNodeCore.create_simple("test_func", "Test function")
        node = ModelFunctionNode(core=core)

        assert node.name == "test_func"
        assert node.description == "Test function"
        assert node.core is not None
        assert node.metadata is not None
        assert node.performance is not None

    def test_model_with_all_components(self):
        """Test model with all composed sub-models."""
        core = ModelFunctionNodeCore.create_simple("test_func", "Test function")
        metadata = ModelFunctionNodeMetadata()
        performance = ModelFunctionNodePerformance()

        node = ModelFunctionNode(core=core, metadata=metadata, performance=performance)

        assert node.core == core
        assert node.metadata == metadata
        assert node.performance == performance

    def test_property_delegation_name(self):
        """Test name property delegation to core."""
        core = ModelFunctionNodeCore.create_simple("my_function", "Description")
        node = ModelFunctionNode(core=core)

        assert node.name == "my_function"
        assert node.name == node.core.name

    def test_property_delegation_description(self):
        """Test description property delegation to core."""
        core = ModelFunctionNodeCore.create_simple("func", "My description")
        node = ModelFunctionNode(core=core)

        assert node.description == "My description"
        assert node.description == node.core.description

    def test_property_delegation_status(self):
        """Test status property delegation to core."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        assert node.status == EnumFunctionStatus.ACTIVE
        assert node.status == node.core.status

    def test_property_delegation_parameters(self):
        """Test parameters property delegation to core."""
        core = ModelFunctionNodeCore.create_from_signature(
            "func",
            ["param1", "param2"],
        )
        node = ModelFunctionNode(core=core)

        assert node.parameters == ["param1", "param2"]
        assert node.parameters == node.core.parameters

    def test_property_delegation_complexity(self):
        """Test complexity property delegation to performance."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        assert node.complexity == node.performance.complexity

    def test_property_delegation_tags(self):
        """Test tags property delegation to metadata."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        assert node.tags == node.metadata.tags

    def test_is_active_method(self):
        """Test is_active method delegation."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        core.status = EnumFunctionStatus.ACTIVE
        node = ModelFunctionNode(core=core)

        assert node.is_active() is True

    def test_is_disabled_method(self):
        """Test is_disabled method delegation."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        core.status = EnumFunctionStatus.DISABLED
        node = ModelFunctionNode(core=core)

        assert node.is_disabled() is True

    def test_get_complexity_level(self):
        """Test get_complexity_level method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        complexity_level = node.get_complexity_level()
        assert isinstance(complexity_level, int)
        assert complexity_level >= 1

    def test_has_documentation(self):
        """Test has_documentation method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        metadata = ModelFunctionNodeMetadata.create_documented("Test docstring")
        node = ModelFunctionNode(core=core, metadata=metadata)

        assert node.has_documentation() is True

    def test_has_examples(self):
        """Test has_examples method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        metadata = ModelFunctionNodeMetadata.create_documented(
            "Docstring",
            ["example1", "example2"],
        )
        node = ModelFunctionNode(core=core, metadata=metadata)

        assert node.has_examples() is True

    def test_get_parameter_count(self):
        """Test get_parameter_count method."""
        core = ModelFunctionNodeCore.create_from_signature(
            "func",
            ["p1", "p2", "p3"],
        )
        node = ModelFunctionNode(core=core)

        assert node.get_parameter_count() == 3

    def test_has_type_annotations(self):
        """Test has_type_annotations method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        core.return_type = EnumReturnType.TEXT
        node = ModelFunctionNode(core=core)

        assert node.has_type_annotations() is True

    def test_add_tag(self):
        """Test add_tag method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node.add_tag("test_tag")
        assert "test_tag" in node.tags

        # Adding same tag again shouldn't duplicate
        node.add_tag("test_tag")
        assert node.tags.count("test_tag") == 1

    def test_remove_tag(self):
        """Test remove_tag method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node.add_tag("test_tag")
        assert "test_tag" in node.tags

        node.remove_tag("test_tag")
        assert "test_tag" not in node.tags

    def test_add_category(self):
        """Test add_category method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node.add_category(EnumCategory.CORE)
        assert EnumCategory.CORE in node.metadata.categories

    def test_add_example(self):
        """Test add_example method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node.add_example("example usage")
        assert "example usage" in node.metadata.documentation.examples

    def test_add_note(self):
        """Test add_note method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node.add_note("important note")
        assert "important note" in node.metadata.documentation.notes

    def test_update_timestamp(self):
        """Test update_timestamp method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        original_timestamp = node.metadata.updated_at
        node.update_timestamp()
        assert node.metadata.updated_at >= original_timestamp

    def test_validate_function(self):
        """Test validate_function method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node.validate_function()
        assert node.metadata.last_validated is not None

    def test_record_execution(self):
        """Test record_execution method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node.record_execution(success=True, execution_time_ms=10.5, memory_used_mb=5.0)

        assert node.performance.execution_count == 1
        assert node.performance.success_rate == 1.0

    def test_has_tests_raises_not_implemented(self):
        """Test has_tests raises NotImplementedError (TODO stub)."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        with pytest.raises(NotImplementedError) as exc_info:
            node.has_tests()

        assert "Test detection not yet implemented" in str(exc_info.value)
        assert "GitHub issue #47" in str(exc_info.value)

    def test_implementation_property_raises_not_implemented(self):
        """Test implementation property raises NotImplementedError (TODO stub)."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        with pytest.raises(NotImplementedError) as exc_info:
            _ = node.implementation

        assert "Source code retrieval not yet implemented" in str(exc_info.value)
        assert "GitHub issue #49" in str(exc_info.value)

    def test_to_summary(self):
        """Test to_summary method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        summary = node.to_summary()

        assert summary.function_name == "func"
        assert summary.description == "Description"
        assert summary.has_tests is False  # Graceful handling of NotImplementedError

    def test_create_simple_factory(self):
        """Test create_simple factory method."""
        node = ModelFunctionNode.create_simple("test_func", "Test description")

        assert node.name == "test_func"
        assert node.description == "Test description"

    def test_create_simple_with_function_type(self):
        """Test create_simple with function type."""
        node = ModelFunctionNode.create_simple(
            "test_func",
            "Description",
            function_type="compute",
        )

        assert node.name == "test_func"
        assert node.core.function_type == EnumFunctionType.COMPUTE

    def test_create_simple_with_invalid_function_type(self):
        """Test create_simple with invalid function type raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            ModelFunctionNode.create_simple(
                "test_func",
                "Description",
                function_type="invalid_type",
            )

        assert "Invalid function type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)

    def test_create_from_signature_factory(self):
        """Test create_from_signature factory method."""
        node = ModelFunctionNode.create_from_signature(
            "test_func",
            ["param1", "param2"],
            return_type="TEXT",
            description="Test function",
        )

        assert node.name == "test_func"
        assert node.parameters == ["param1", "param2"]
        assert node.core.return_type == EnumReturnType.TEXT

    def test_create_from_signature_with_invalid_return_type(self):
        """Test create_from_signature with invalid return type raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            ModelFunctionNode.create_from_signature(
                "test_func",
                ["param1"],
                return_type="invalid_type",
            )

        assert "Invalid return type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)

    def test_create_documented_factory(self):
        """Test create_documented factory method."""
        node = ModelFunctionNode.create_documented(
            "test_func",
            "Description",
            "Detailed docstring",
            examples=["example1", "example2"],
        )

        assert node.name == "test_func"
        assert node.has_documentation() is True
        assert node.has_examples() is True

    def test_create_with_performance_factory(self):
        """Test create_with_performance factory method."""
        performance = ModelFunctionNodePerformance()
        performance.cyclomatic_complexity = 10

        node = ModelFunctionNode.create_with_performance(
            "test_func",
            "Description",
            performance=performance,
        )

        assert node.name == "test_func"
        assert node.performance.cyclomatic_complexity == 10

    def test_get_id_protocol(self):
        """Test get_id protocol method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        node_id = node.get_id()
        assert isinstance(node_id, str)
        assert len(node_id) > 0

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        metadata = node.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        # Test setting a valid field returns True
        result = node.set_metadata({"core": core})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        serialized = node.serialize()
        assert isinstance(serialized, dict)
        assert "core" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        assert node.validate_instance() is True

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")

        # Should not raise error with extra fields
        node = ModelFunctionNode(core=core, extra_field="ignored")
        assert node.name == "func"

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        core = ModelFunctionNodeCore.create_simple("func", "Description")
        node = ModelFunctionNode(core=core)

        # Should validate new assignments
        node.core = ModelFunctionNodeCore.create_simple("new_func", "New desc")
        assert node.name == "new_func"
