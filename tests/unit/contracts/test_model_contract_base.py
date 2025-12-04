#!/usr/bin/env python3
"""
ModelContractBase Comprehensive Unit Tests - Zero Tolerance Testing

This module provides comprehensive test coverage for ModelContractBase,
the abstract foundation for all contract models in the ONEX framework.

Coverage Requirements:
- >95% line coverage for all methods
- 100% coverage for error handling paths
- Comprehensive edge case and boundary condition testing
- Memory safety validation with large data structures

ZERO TOLERANCE: Every code path must be tested thoroughly.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dependency_type import EnumDependencyType
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


# Concrete implementation for testing abstract base class
class TestableContractModel(ModelContractBase):
    """Concrete implementation of ModelContractBase for testing purposes."""

    def validate_node_specific_config(self) -> None:
        """Test implementation of abstract method."""
        # Simple validation for testing
        if self.name == "invalid_test_contract":
            # Use ValueError instead of ValidationError for simpler testing
            raise ValueError("Test validation error")


class TestModelContractBase:
    """Comprehensive tests for ModelContractBase with zero tolerance coverage."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.valid_semver = ModelSemVer(major=1, minor=0, patch=0)
        self.valid_dependency = ModelDependency(
            name="TestProtocol",
            module="omnibase_core.protocol.test_protocol",
            dependency_type=EnumDependencyType.PROTOCOL,
            required=True,
            description="Test protocol dependency",
        )

        self.minimal_valid_data = {
            "name": "test_contract",
            "version": self.valid_semver,
            "description": "Test contract description",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "omnibase_core.models.test.TestInputModel",
            "output_model": "omnibase_core.models.test.TestOutputModel",
        }

    # =================== VALID CONSTRUCTION TESTS ===================

    def test_valid_construction_minimal_required_fields(self):
        """Test valid construction with only required fields."""
        contract = TestableContractModel(**self.minimal_valid_data)

        assert contract.name == "test_contract"
        assert contract.version == self.valid_semver
        assert contract.description == "Test contract description"
        assert contract.node_type == EnumNodeType.COMPUTE_GENERIC
        assert contract.input_model == "omnibase_core.models.test.TestInputModel"
        assert contract.output_model == "omnibase_core.models.test.TestOutputModel"

        # Test default values
        assert contract.dependencies == []
        assert contract.protocol_interfaces == []
        assert contract.tags == []
        assert contract.author is None
        assert contract.documentation_url is None

    def test_valid_construction_all_fields_populated(self):
        """Test valid construction with all fields populated."""
        full_data = {
            **self.minimal_valid_data,
            "dependencies": [self.valid_dependency],
            "protocol_interfaces": ["omnibase_core.protocol.test_interface"],
            "tags": ["compute", "test", "validation"],
            "author": "ONEX Test Team",
            "documentation_url": "https://docs.onex.systems/contracts/test_contract",
        }

        contract = TestableContractModel(**full_data)

        assert len(contract.dependencies) == 1
        assert contract.dependencies[0].name == "TestProtocol"
        assert contract.protocol_interfaces == ["omnibase_core.protocol.test_interface"]
        assert contract.tags == ["compute", "test", "validation"]
        assert contract.author == "ONEX Test Team"
        assert (
            contract.documentation_url
            == "https://docs.onex.systems/contracts/test_contract"
        )

    # =================== FIELD VALIDATION TESTS ===================

    def test_required_field_validation_name(self):
        """Test name field validation requirements."""
        data = {**self.minimal_valid_data}

        # Test missing name
        del data["name"]
        with pytest.raises(ValidationError, match="name"):
            TestableContractModel(**data)

        # Test empty name
        data["name"] = ""
        with pytest.raises(ValidationError, match="at least 1 character"):
            TestableContractModel(**data)

        # Test whitespace-only name - should be stripped to empty and fail validation
        data["name"] = "   "
        with pytest.raises(ValidationError, match="at least 1 character"):
            TestableContractModel(
                **data,
            )  # Pydantic strips whitespace, then validates min_length

    def test_required_field_validation_description(self):
        """Test description field validation requirements."""
        data = {**self.minimal_valid_data}

        # Test missing description
        del data["description"]
        with pytest.raises(ValidationError, match="description"):
            TestableContractModel(**data)

        # Test empty description
        data["description"] = ""
        with pytest.raises(ValidationError, match="at least 1 character"):
            TestableContractModel(**data)

    def test_input_output_model_validation(self):
        """Test input_model and output_model field validation."""
        test_data = {**self.minimal_valid_data}

        # Test missing input_model
        del test_data["input_model"]
        with pytest.raises(ValidationError, match="input_model"):
            TestableContractModel(**test_data)

        # Test empty input_model
        test_data["input_model"] = ""
        with pytest.raises(ValidationError, match="at least 1 character"):
            TestableContractModel(**test_data)

    # =================== NODE TYPE VALIDATION TESTS ===================

    def test_node_type_enum_validation_valid_enum(self):
        """Test node_type validation with valid EnumNodeType values."""
        for node_type in EnumNodeType:
            data = {**self.minimal_valid_data, "node_type": node_type}
            contract = TestableContractModel(**data)
            assert contract.node_type == node_type

    def test_node_type_string_conversion_yaml_support(self):
        """Test node_type string conversion for YAML deserialization."""
        # Test valid string conversion
        data = {**self.minimal_valid_data, "node_type": "COMPUTE"}
        contract = TestableContractModel(**data)
        assert contract.node_type == EnumNodeType.COMPUTE_GENERIC

    def test_node_type_invalid_string_raises_onex_error(self):
        """Test node_type validation with invalid string raises ModelOnexError."""
        data = {**self.minimal_valid_data, "node_type": "invalid_node_type"}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.model.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "invalid_node_type" in error.message
        assert "valid EnumNodeType value" in error.message
        assert error.model.context is not None
        assert "invalid_value" in error.model.context

    def test_node_type_invalid_type_raises_onex_error(self):
        """Test node_type validation with invalid type raises ModelOnexError."""
        data = {**self.minimal_valid_data, "node_type": 123}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "EnumNodeType enum or valid string" in error.message

    # =================== DEPENDENCY VALIDATION TESTS ===================

    def test_dependencies_validation_empty_list(self):
        """Test dependencies validation with empty list."""
        data = {**self.minimal_valid_data, "dependencies": []}
        contract = TestableContractModel(**data)
        assert contract.dependencies == []

    def test_dependencies_validation_valid_model_dependency_list(self):
        """Test dependencies validation with valid ModelDependency objects."""
        deps = [
            ModelDependency(
                name="Protocol1",
                module="omnibase_core.protocol.protocol1",
                dependency_type=EnumDependencyType.PROTOCOL,
            ),
            ModelDependency(
                name="Protocol2",
                module="omnibase_core.protocol.protocol2",
                dependency_type=EnumDependencyType.SERVICE,
            ),
        ]

        data = {**self.minimal_valid_data, "dependencies": deps}
        contract = TestableContractModel(**data)
        assert len(contract.dependencies) == 2
        assert contract.dependencies[0].name == "Protocol1"
        assert contract.dependencies[1].name == "Protocol2"

    def test_dependencies_validation_dict_yaml_conversion(self):
        """Test dependencies validation with dict conversion for YAML loading."""
        dict_deps = [
            {
                "name": "YamlProtocol",
                "module": "omnibase_core.protocol.yaml_protocol",
                "dependency_type": "protocol",
                "required": True,
                "description": "YAML loaded protocol",
            },
        ]

        data = {**self.minimal_valid_data, "dependencies": dict_deps}
        contract = TestableContractModel(**data)
        assert len(contract.dependencies) == 1
        assert contract.dependencies[0].name == "YamlProtocol"
        assert contract.dependencies[0].dependency_type == EnumDependencyType.PROTOCOL

    def test_dependencies_validation_invalid_type_raises_onex_error(self):
        """Test dependencies validation with invalid type raises ModelOnexError."""
        data = {**self.minimal_valid_data, "dependencies": "invalid_string"}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be a list" in error.message

    def test_dependencies_validation_string_dependency_security_rejection(self):
        """Test dependencies validation rejects string dependencies for security."""
        string_deps = ["string_dependency", "another_string"]

        data = {**self.minimal_valid_data, "dependencies": string_deps}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.model.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Batch validation failed" in error.message
        assert "string_dependency" in str(error.model.context)

    def test_dependencies_memory_safety_limit_enforcement(self):
        """Test dependencies validation enforces memory safety limits."""
        # Create more than the maximum allowed dependencies (100)
        large_deps = [
            {"name": f"Protocol{i}", "module": f"module{i}"} for i in range(101)
        ]

        data = {**self.minimal_valid_data, "dependencies": large_deps}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Too many dependencies" in error.message
        assert "101" in error.message
        assert "100" in error.message

    def test_dependencies_batch_validation_mixed_types(self):
        """Test dependencies batch validation with mixed valid/invalid types."""
        mixed_deps = [
            self.valid_dependency,  # Valid ModelDependency
            {"name": "DictDep", "module": "test.module"},  # Valid dict
            "invalid_string",  # Invalid string
            123,  # Invalid type
        ]

        data = {**self.minimal_valid_data, "dependencies": mixed_deps}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Batch validation failed" in error.message

    # =================== POST-INIT VALIDATION TESTS ===================

    def test_circular_dependency_detection_direct_self_dependency(self):
        """Test detection of direct circular dependencies."""
        self_dep = ModelDependency(
            name="test_contract",  # Same as contract name
            module="omnibase_core.protocol.test_protocol",  # Contains 'protocol' for ONEX compliance
            dependency_type=EnumDependencyType.PROTOCOL,
        )

        data = {**self.minimal_valid_data, "dependencies": [self_dep]}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Direct circular dependency" in error.message
        assert "test_contract" in error.message

    def test_circular_dependency_detection_duplicate_dependencies(self):
        """Test detection of duplicate dependencies."""
        dup_deps = [
            ModelDependency(name="DuplicateProtocol", module="test.module"),
            ModelDependency(name="DuplicateProtocol", module="test.other"),  # Same name
        ]

        data = {**self.minimal_valid_data, "dependencies": dup_deps}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Duplicate dependency detected" in error.message

    def test_circular_dependency_detection_module_reference(self):
        """Test detection of potential circular dependencies through modules."""
        module_dep = ModelDependency(
            name="ModuleProtocol",
            module="omnibase_core.contracts.test_contract_module",  # Contains contract name
            dependency_type=EnumDependencyType.PROTOCOL,
        )

        data = {**self.minimal_valid_data, "dependencies": [module_dep]}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Potential circular dependency" in error.message

    def test_dependency_complexity_limit_enforcement(self):
        """Test enforcement of dependency complexity limits."""
        # Create exactly 51 dependencies (over the 50 limit)
        many_deps = [
            ModelDependency(name=f"Protocol{i}", module=f"module{i}") for i in range(51)
        ]

        data = {**self.minimal_valid_data, "dependencies": many_deps}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "too many dependencies" in error.message
        assert "51" in error.message

    def test_protocol_interface_validation(self):
        """Test protocol interface validation requirements."""
        # Valid protocol interface
        data = {
            **self.minimal_valid_data,
            "protocol_interfaces": ["omnibase_core.protocol.test_interface"],
        }
        contract = TestableContractModel(**data)
        assert "omnibase_core.protocol.test_interface" in contract.protocol_interfaces

        # Invalid protocol interface (missing 'protocol' in name)
        invalid_data = {
            **self.minimal_valid_data,
            "protocol_interfaces": ["omnibase_core.invalid.interface"],
        }
        with pytest.raises(
            ModelOnexError,
            match="Protocol interface must contain 'protocol'",
        ):
            TestableContractModel(**invalid_data)

    # =================== MEMORY SAFETY AND PERFORMANCE TESTS ===================

    def test_memory_safety_large_dependency_lists(self):
        """Test memory safety with large but valid dependency lists."""
        # Create maximum allowed dependencies (50 - complexity limit)
        max_deps = [
            ModelDependency(name=f"Protocol{i}", module=f"module{i}") for i in range(50)
        ]

        data = {**self.minimal_valid_data, "dependencies": max_deps}
        contract = TestableContractModel(**data)

        assert len(contract.dependencies) == 50
        assert contract.dependencies[0].name == "Protocol0"
        assert contract.dependencies[49].name == "Protocol49"

    def test_memory_safety_large_protocol_interfaces(self):
        """Test memory safety with large protocol interface lists."""
        large_interfaces = [f"omnibase_core.protocol.interface{i}" for i in range(50)]

        data = {**self.minimal_valid_data, "protocol_interfaces": large_interfaces}
        contract = TestableContractModel(**data)

        assert len(contract.protocol_interfaces) == 50

    def test_memory_safety_large_tags_list(self):
        """Test memory safety with large tag lists."""
        large_tags = [f"tag{i}" for i in range(100)]

        data = {**self.minimal_valid_data, "tags": large_tags}
        contract = TestableContractModel(**data)

        assert len(contract.tags) == 100

    # =================== EDGE CASE AND BOUNDARY CONDITION TESTS ===================

    def test_edge_case_empty_strings_after_whitespace_stripping(self):
        """Test edge cases with whitespace handling."""
        data = {
            **self.minimal_valid_data,
            "name": "   test_contract   ",  # Should be stripped
            "description": "   description   ",  # Should be stripped
            "author": "   ",  # Should become empty string
        }

        contract = TestableContractModel(**data)
        assert contract.name == "test_contract"
        assert contract.description == "description"
        assert contract.author == ""  # Whitespace stripped

    def test_edge_case_unicode_strings(self):
        """Test edge cases with Unicode strings."""
        unicode_data = {
            **self.minimal_valid_data,
            "name": "test_contract_🔥",
            "description": "Contract with émojis and spëcial chars",
            "author": "测试作者",
        }

        contract = TestableContractModel(**unicode_data)
        assert "🔥" in contract.name
        assert "émojis" in contract.description
        assert contract.author == "测试作者"

    def test_edge_case_very_long_strings(self):
        """Test edge cases with very long strings."""
        long_string = "a" * 10000

        data = {**self.minimal_valid_data, "description": long_string}

        contract = TestableContractModel(**data)
        assert len(contract.description) == 10000

    # =================== ABSTRACT METHOD TESTING ===================

    def test_abstract_method_validate_node_specific_config(self):
        """Test abstract method validate_node_specific_config is called."""
        # Test successful validation
        contract = TestableContractModel(**self.minimal_valid_data)
        assert contract.name == "test_contract"

        # Test validation error propagation
        error_data = {**self.minimal_valid_data, "name": "invalid_test_contract"}
        with pytest.raises(ValueError):
            TestableContractModel(**error_data)

    # =================== MODEL CONFIGURATION TESTS ===================

    def test_model_config_extra_fields_rejected(self):
        """Test that extra fields are rejected per ZERO TOLERANCE model configuration."""
        data_with_extra = {
            **self.minimal_valid_data,
            "extra_unknown_field": "should_be_rejected",
            "another_extra_field": 12345,
        }

        with pytest.raises(ValidationError) as exc_info:
            TestableContractModel(**data_with_extra)

        # Verify both extra fields are reported in the error
        error_str = str(exc_info.value)
        assert "extra_unknown_field" in error_str
        assert "another_extra_field" in error_str

    def test_model_config_enum_values_preservation(self):
        """Test that enum objects are preserved, not converted to strings."""
        contract = TestableContractModel(**self.minimal_valid_data)
        assert isinstance(contract.node_type, EnumNodeType)
        assert contract.node_type == EnumNodeType.COMPUTE_GENERIC

    # =================== INTEGRATION WITH ONEX ERROR SYSTEM ===================

    def test_onex_error_exception_chaining_preservation(self):
        """Test that ModelOnexError properly chains underlying exceptions."""
        data = {**self.minimal_valid_data, "node_type": "invalid_enum_value"}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        # Verify exception chaining is preserved
        assert error.__cause__ is not None or error.__context__ is not None

    def test_onex_error_context_details_completeness(self):
        """Test that ModelOnexError includes complete context details."""
        data = {**self.minimal_valid_data, "dependencies": "invalid_type"}

        with pytest.raises(ModelOnexError) as exc_info:
            TestableContractModel(**data)

        error = exc_info.value
        assert error.model.context is not None
        # Verify context contains helpful information
        context = error.model.context
        assert "input_type" in context
        assert "expected_type" in context
        assert "example" in context
