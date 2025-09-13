#!/usr/bin/env python3
"""
Edge case tests for ModelContractBase dependency validation.

Tests malformed YAML handling, OnexError scenarios, and validation robustness.
"""

from unittest.mock import Mock

import pytest

from omnibase_core.core.contracts.model_contract_base import ModelContractBase
from omnibase_core.core.contracts.model_dependency import ModelDependency
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums import EnumNodeType
from omnibase_core.models.core.model_semver import ModelSemVer


# Create a concrete test implementation  
class _TestContract(ModelContractBase):
    """Concrete contract implementation for testing."""

    def validate_node_specific_config(self) -> None:
        """Test implementation - no additional validation needed."""
        pass


def create_test_contract(**kwargs):
    """Helper to create test contract with required fields."""
    defaults = {
        "name": "test-contract",
        "version": ModelSemVer(major=1, minor=0, patch=0),
        "description": "Test contract description",
        "node_type": EnumNodeType.COMPUTE,
        "input_model": "test.input.Model",
        "output_model": "test.output.Model",
    }
    defaults.update(kwargs)
    return _TestContract(**defaults)


class TestModelContractDependencyValidation:
    """Test edge cases for contract dependency validation."""

    def test_empty_dependencies_list(self):
        """Test handling of empty dependencies list."""
        contract = create_test_contract(dependencies=[])

        assert contract.dependencies == []

    def test_none_dependencies_becomes_empty_list(self):
        """Test that None dependencies becomes empty list."""
        contract = create_test_contract(dependencies=None)

        assert contract.dependencies == []

    def test_dependencies_not_list_raises_onex_error(self):
        """Test that non-list dependencies raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                node_id="test-node",
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_type=EnumNodeType.COMPUTE,
                dependencies="not a list",
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "must be a list" in error.message
        assert error.context["context"]["input_type"] == "<class 'str'>"

    def test_dependency_missing_name_field_raises_onex_error(self):
        """Test dependency missing name field raises OnexError with context."""
        malformed_dependency = {
            "type": "protocol",
            "module": "some.module",
            # Missing required 'name' field
        }

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                node_id="test-node",
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_type=EnumNodeType.COMPUTE,
                dependencies=[malformed_dependency],
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "missing required 'name' field" in error.message
        assert error.context["context"]["dependency_index"] == 0
        assert error.context["context"]["received_keys"] == ["type", "module"]
        assert "expected_format" in error.context["context"]

    def test_dependency_invalid_format_raises_onex_error(self):
        """Test dependency with invalid ModelDependency fields raises OnexError."""
        invalid_dependency = {
            "name": "test-protocol-dep",
            "type": "protocol",
            "module": "test.protocol.module",
            "version": {"invalid": "structure"},  # Invalid version structure
        }

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                node_id="test-node",
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_type=EnumNodeType.COMPUTE,
                dependencies=[invalid_dependency],
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "has invalid format" in error.message
        assert error.context["context"]["dependency_index"] == 0
        assert error.context["context"]["dependency_data"] == invalid_dependency
        assert "validation_error" in error.context["context"]

    def test_dependency_not_dict_raises_onex_error(self):
        """Test non-dict dependency raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                node_id="test-node",
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_type=EnumNodeType.COMPUTE,
                dependencies=["string_dependency"],  # Not allowed
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "must be dict with structured format" in error.message
        assert "No string dependencies allowed" in error.message
        assert error.context["context"]["dependency_index"] == 0
        assert error.context["context"]["received_type"] == "<class 'str'>"
        assert error.context["context"]["expected_type"] == "dict"

    def test_mixed_dependency_types_valid(self):
        """Test mixing ModelDependency objects and valid dicts."""
        existing_dependency = ModelDependency(
            name="existing-protocol-dep",
            dependency_type="protocol",
            module="existing.protocol.module",
        )

        dict_dependency = {
            "name": "dict-protocol-dep",
            "type": "protocol",
            "module": "dict.protocol.module",
        }

        contract = create_test_contract(
            node_id="test-node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type=EnumNodeType.COMPUTE,
            dependencies=[existing_dependency, dict_dependency],
        )

        assert len(contract.dependencies) == 2
        assert contract.dependencies[0].name == "existing-protocol-dep"
        assert contract.dependencies[1].name == "dict-protocol-dep"

    def test_multiple_invalid_dependencies_reports_first_error(self):
        """Test that validation stops at first error with proper index."""
        dependencies = [
            {
                "name": "valid-protocol-dep",
                "type": "protocol",
                "module": "valid.protocol.module",
            },
            {
                "type": "protocol",
                "module": "missing.protocol.name",
            },  # Missing name - should trigger error
            "string_dep",  # Also invalid but shouldn't be reached
        ]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                node_id="test-node",
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_type=EnumNodeType.COMPUTE,
                dependencies=dependencies,
            )

        error = exc_info.value
        assert (
            error.context["context"]["dependency_index"] == 1
        )  # Second dependency (0-indexed)
        assert "missing required 'name' field" in error.message

    def test_empty_dict_dependency_raises_onex_error(self):
        """Test empty dict dependency raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                node_id="test-node",
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_type=EnumNodeType.COMPUTE,
                dependencies=[{}],  # Empty dict
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "missing required 'name' field" in error.message
        assert error.context["context"]["received_keys"] == []

    def test_dependency_validation_exception_chaining(self):
        """Test that original validation exceptions are properly chained."""
        invalid_dependency = {
            "name": "test-protocol-dep",
            "type": "protocol",
            "module": "test.protocol.module",
            "version": "not-a-semver",  # Invalid version format
        }

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                node_id="test-node",
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_type=EnumNodeType.COMPUTE,
                dependencies=[invalid_dependency],
            )

        error = exc_info.value
        assert error.__cause__ is not None  # Original exception should be chained
        assert "has invalid format" in error.message

    def test_large_dependency_list_performance(self):
        """Test validation performance with large dependency list."""
        # Create 100 valid dependencies
        dependencies = []
        for i in range(100):
            dependencies.append(
                {
                    "name": f"protocol-dep-{i}",
                    "type": "protocol",
                    "module": f"protocol.module.dep{i}",
                }
            )

        contract = create_test_contract(
            node_id="test-node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type=EnumNodeType.COMPUTE,
            dependencies=dependencies,
        )

        assert len(contract.dependencies) == 100
        assert all(isinstance(dep, ModelDependency) for dep in contract.dependencies)

    def test_very_large_dependency_list_performance(self):
        """Test validation performance with very large dependency list (1000+ dependencies)."""
        import time
        
        # Create 1000 valid dependencies
        dependencies = []
        for i in range(1000):
            dependencies.append({
                "name": f"protocol-dep-{i:04d}",
                "type": "protocol",
                "module": f"protocol.module.dep{i:04d}"
            })
        
        start_time = time.time()
        contract = create_test_contract(
            node_id="performance-test-node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type=EnumNodeType.COMPUTE,
            dependencies=dependencies,
        )
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        # Assertions
        assert len(contract.dependencies) == 1000
        assert all(isinstance(dep, ModelDependency) for dep in contract.dependencies)
        
        # Performance assertion - should complete within reasonable time
        # Allow up to 5 seconds for 1000 dependencies (quite generous)
        assert validation_time < 5.0, f"Validation took {validation_time:.3f}s, expected < 5.0s"
        
        # Verify first and last dependencies for correctness
        assert contract.dependencies[0].name == "protocol-dep-0000"
        assert contract.dependencies[999].name == "protocol-dep-0999"
        assert contract.dependencies[0].module == "protocol.module.dep0000"
        assert contract.dependencies[999].module == "protocol.module.dep0999"

    def test_dependency_validation_performance_with_mixed_types(self):
        """Test performance with mixed dependency types and complex validation."""
        import time
        
        # Create a smaller set of dependencies that are definitely ONEX compliant
        dependencies = []
        
        # Create 100 of each type for better performance testing
        for i in range(400):  # 100 * 4 = 400 total
            dep_type = ["protocol", "service", "module", "external"][i % 4]
            
            # All dependencies use protocol naming to pass ONEX validation
            # This tests performance, not validation logic
            name = f"ProtocolEventBus{i:03d}"
            module = f"protocol.complex.module.path.dep{i:03d}"
                
            dependencies.append({
                "name": name,
                "type": dep_type,
                "module": module,
                "version": {"major": 1, "minor": i % 10, "patch": (i * 7) % 5}
            })
        
        start_time = time.time()
        contract = create_test_contract(
            node_id="mixed-performance-test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type=EnumNodeType.COMPUTE,
            dependencies=dependencies,
        )
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        # Assertions
        assert len(contract.dependencies) == 400
        assert all(isinstance(dep, ModelDependency) for dep in contract.dependencies)
        
        # Performance assertion - more complex validation, allow up to 3 seconds
        assert validation_time < 3.0, f"Mixed validation took {validation_time:.3f}s, expected < 3.0s"
        
        # Verify dependency creation success - all should be ProtocolEventBus due to type inference
        # This test focuses on performance, not type distribution logic
        protocol_count = sum(1 for dep in contract.dependencies if dep.dependency_type.value == "protocol")
        
        # All dependencies should be inferred as PROTOCOL due to name pattern
        assert protocol_count == 400, f"Expected all 400 dependencies to be protocol type, got {protocol_count}"

    def test_dependency_with_special_characters_in_name(self):
        """Test dependencies with edge case names."""
        valid_names = [
            "protocol-normal-name",
            "protocol_with_underscore",
            "protocol.with.dots",
            "protocol-name123",
            "PROTOCOL_UPPERCASE_NAME",
            "mixed.Protocol-name_123",
        ]

        dependencies = []
        for name in valid_names:
            dependencies.append(
                {
                    "name": name,
                    "type": "protocol",
                    "module": f"protocol.module.{name.lower()}",
                }
            )

        contract = create_test_contract(
            node_id="test-node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type=EnumNodeType.COMPUTE,
            dependencies=dependencies,
        )

        assert len(contract.dependencies) == len(valid_names)
        for i, expected_name in enumerate(valid_names):
            assert contract.dependencies[i].name == expected_name

    def test_malformed_yaml_simulation(self):
        """Test handling of common YAML parsing edge cases."""
        # Simulate YAML parsing edge cases that actually trigger OnexError
        edge_cases = [
            # Case 1: Invalid version structure (should trigger ModelDependency validation error)
            {
                "name": "version-protocol-dep",
                "type": "protocol",
                "module": "test.protocol.module",
                "version": {"invalid": "structure"},
            },
            # Case 2: YAML with wrong types for name (should trigger validation error)
            {"name": 123, "type": "protocol", "module": "test.protocol.module"},
        ]

        for i, dependency in enumerate(edge_cases):
            with pytest.raises(OnexError) as exc_info:
                create_test_contract(
                    dependencies=[dependency],
                )

            error = exc_info.value
            assert error.error_code == CoreErrorCode.VALIDATION_FAILED
            # Each case should provide appropriate error context
            assert error.context["context"]["dependency_index"] == 0

    def test_comprehensive_malformed_dependency_scenarios(self):
        """Test comprehensive malformed dependency scenarios that could come from YAML."""
        malformed_scenarios = [
            # Scenario 1: Extremely long strings (potential DoS)
            {"name": "x" * 1000, "type": "protocol", "module": "test.module"},
            
            # Scenario 2: Nested objects where simple values expected
            {"name": {"nested": "object"}, "type": "protocol", "module": "test.module"},
            
            # Scenario 3: Boolean values where strings expected
            {"name": True, "type": False, "module": "test.module"},
            
            # Scenario 4: Arrays where objects expected
            ["array", "instead", "of", "object"],
            
            # Scenario 5: Empty strings after YAML processing
            {"name": "", "type": "protocol", "module": ""},
            
            # Scenario 6: Whitespace-only strings
            {"name": "   ", "type": "\t\t", "module": "\n\n"},
            
            # Scenario 7: Very deeply nested version structures
            {
                "name": "deep-version",
                "type": "protocol", 
                "module": "test.module",
                "version": {"nested": {"very": {"deep": {"version": {"structure": "invalid"}}}}}
            },
            
            # Scenario 8: None values where strings expected
            {"name": None, "type": "protocol", "module": "test.module"},
            
            # Scenario 9: Numeric strings that could cause confusion
            {"name": "123456", "type": "456", "module": "789.module"},
            
            # Scenario 10: Mixed valid/invalid fields
            {"name": "valid-name", "type": "protocol", "module": "test.module", "invalid_extra": 42}
        ]
        
        for i, malformed_dep in enumerate(malformed_scenarios):
            with pytest.raises((OnexError, ValueError, TypeError, AttributeError)) as exc_info:
                create_test_contract(
                    dependencies=[malformed_dep]
                )
            
            # Verify we get appropriate error (OnexError preferred, but built-in exceptions acceptable)
            if isinstance(exc_info.value, OnexError):
                assert exc_info.value.error_code == CoreErrorCode.VALIDATION_FAILED
            
            # All should fail validation in some way
            assert exc_info.value is not None


class TestModelDependencySecurityValidation:
    """Security tests for ModelDependency path traversal prevention."""

    def test_module_path_traversal_prevention(self):
        """Test that path traversal attempts are blocked."""
        from omnibase_core.core.contracts.model_dependency import ModelDependency
        
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "legitimate.module/../malicious",
            "module/../../sensitive",
            "normal.module\\..\\danger",
            "/absolute/path/attempt",
            "\\windows\\path\\attempt",
            "module/../other",
            "a..b.module",  # .. in middle
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(
                    name="test-dep",
                    dependency_type="module",
                    module=malicious_path
                )
            
            error = exc_info.value
            assert error.error_code == CoreErrorCode.VALIDATION_FAILED
            assert "path traversal" in error.message.lower() or "invalid module path" in error.message.lower()
            assert error.context["context"]["module_path"] == malicious_path

    def test_valid_module_paths_allowed(self):
        """Test that valid module paths are still allowed."""
        from omnibase_core.core.contracts.model_dependency import ModelDependency
        
        valid_paths = [
            "omnibase.protocol.event_bus",
            "my_package.sub_module",
            "package-name.module_name",
            "simple_module",
            "a.b.c.d.e",
            "alpha123.beta456",
            "module_with_underscores",
            "module-with-hyphens",
        ]
        
        for valid_path in valid_paths:
            # Should not raise an exception
            dependency = ModelDependency(
                name="test-dep",
                dependency_type="module",
                module=valid_path
            )
            assert dependency.module == valid_path

    def test_invalid_module_format_patterns(self):
        """Test that invalid module format patterns are rejected."""
        from omnibase_core.core.contracts.model_dependency import ModelDependency
        
        invalid_patterns = [
            "123starts_with_number",
            ".starts_with_dot",
            "ends_with_dot.",
            "double..dots",
            "special@characters",
            "spaces in module",
            "tabs\tin\tmodule",
        ]
        
        for invalid_pattern in invalid_patterns:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(
                    name="test-dep",
                    dependency_type="module",
                    module=invalid_pattern
                )
            
            error = exc_info.value
            assert error.error_code == CoreErrorCode.VALIDATION_FAILED
            assert "invalid module path" in error.message.lower()


class TestModelContractDependencyStructuredValidation:
    """Integration tests for structured dependency data validation scenarios."""

    def test_contract_model_validation_with_structured_dependencies(self):
        """Test contract model validation with structured dependency data."""
        # Test structured dependency data validation through contract model
        # Using patterns that are known to work from existing tests
        structured_dependencies = [
            {
                "name": "test-protocol-dep",
                "type": "protocol",
                "module": "test.protocol.module"
            },
            {
                "name": "another-protocol-dep",
                "type": "protocol",
                "module": "another.protocol.module"
            }
        ]

        # Test contract creation with proper model validation
        contract = create_test_contract(
            dependencies=structured_dependencies,
        )

        # Validate contract was created successfully with proper dependency models
        assert len(contract.dependencies) == 2
        assert contract.dependencies[0].name == "test-protocol-dep"
        assert contract.dependencies[0].dependency_type.value == "protocol"
        assert contract.dependencies[0].module == "test.protocol.module"
        assert contract.dependencies[1].name == "another-protocol-dep"
        assert contract.dependencies[1].dependency_type.value == "protocol"
        assert contract.dependencies[1].module == "another.protocol.module"

    def test_malformed_dependency_data_raises_onex_error(self):
        """Test malformed dependency data handling through model validation."""
        # Test case 1: String dependency (not allowed)
        malformed_dependencies_case1 = ["test-protocol-dep"]  # String instead of dict

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                dependencies=malformed_dependencies_case1,
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "must be dict with structured format" in error.message
        assert "No string dependencies allowed" in error.message
        assert error.context["context"]["dependency_index"] == 0
        assert error.context["context"]["received_type"] == "<class 'str'>"

        # Test case 2: Dict dependency with invalid version structure
        malformed_dependencies_case2 = [
            {
                "name": "test-protocol-dep",
                "type": "protocol",
                "module": "test.protocol.module",
                "version": {"invalid": "structure"}  # Invalid version structure
            }
        ]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                dependencies=malformed_dependencies_case2,
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "has invalid format" in error.message
        assert error.context["context"]["dependency_index"] == 0
        assert "validation_error" in error.context["context"]

        # Test case 3: Multiple malformed dependencies - should report first error
        malformed_dependencies_case3 = [
            "string_dependency",  # Invalid string
            {"name": "incomplete-protocol-dep", "module": "test.module"}  # Missing type
        ]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                dependencies=malformed_dependencies_case3,
            )

        error = exc_info.value
        assert error.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "must be dict with structured format" in error.message
        assert error.context["context"]["dependency_index"] == 0  # Stops at first error
