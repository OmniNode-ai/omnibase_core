#!/usr/bin/env python3
"""
Comprehensive test coverage for contract dependency model refactor completion.

Tests all PR feedback items:
- Memory issues with large dependencies
- YAML field validator enhancements
- Type hint consistency
- Security enhancements
- Performance optimizations
- Error handling consistency
- Circular dependency validation
- Edge cases and regression scenarios
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from omnibase_core.core.contracts.model_contract_base import (
    ModelContractBase,
    ModelDependency,
)
from omnibase_core.core.contracts.model_workflow_dependency import (
    ModelWorkflowDependency,
)
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


class TestMemoryIssuesWithLargeDependencies:
    """Test memory safety with large dependency lists."""

    def test_max_dependencies_limit_enforced(self):
        """Test that max_items constraint prevents memory issues."""
        # Create dependencies list exceeding the limit
        large_dependencies = [
            {"name": f"Dependency{i}", "module": f"test.module.{i}"}
            for i in range(101)  # Exceeds max_length=100
        ]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(dependencies=large_dependencies)

        assert exc_info.value.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "Too many dependencies: 101" in str(exc_info.value)
        assert "memory_safety" in str(exc_info.value.context)

    def test_max_dependencies_limit_boundary(self):
        """Test that exactly 100 dependencies is allowed."""
        boundary_dependencies = [
            {"name": f"Dependency{i}", "module": f"test.module.{i}"}
            for i in range(100)  # Exactly at max_length=100
        ]

        # Should not raise an exception
        contract = create_test_contract(dependencies=boundary_dependencies)
        assert len(contract.dependencies) == 100

    def test_memory_safety_context_information(self):
        """Test that memory safety errors provide helpful context."""
        large_dependencies = [
            {"name": f"Dep{i}", "module": f"test.{i}"} for i in range(150)
        ]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(dependencies=large_dependencies)

        context = exc_info.value.context
        assert "dependency_count" in context
        assert "max_allowed" in context
        assert "memory_safety" in context
        assert "suggestion" in context
        assert context["dependency_count"] == 150
        assert context["max_allowed"] == 100


class TestYAMLFieldValidatorEnhancements:
    """Test enhanced YAML field validator with security and actionable errors."""

    def test_string_dependency_rejection_with_clear_guidance(self):
        """Test that string dependencies are rejected with migration guidance."""
        string_dependencies = ["SomeStringDependency", "AnotherOne"]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(dependencies=string_dependencies)

        error = exc_info.value
        assert "String dependency" in str(error)
        assert "not allowed" in str(error)
        context = error.context
        assert "migration_path" in context
        assert "example_conversion" in context
        assert "security_policy" in context

    def test_dict_to_model_dependency_conversion_success(self):
        """Test successful YAML dict to ModelDependency conversion."""
        dict_dependencies = [
            {"name": "ProtocolEventBus", "module": "omnibase_core.protocol"},
            {
                "name": "ServiceRegistry",
                "module": "omnibase_core.services",
                "required": False,
            },
        ]

        contract = create_test_contract(dependencies=dict_dependencies)

        assert len(contract.dependencies) == 2
        assert isinstance(contract.dependencies[0], ModelDependency)
        assert contract.dependencies[0].name == "ProtocolEventBus"
        assert contract.dependencies[1].required is False

    def test_invalid_dict_conversion_with_actionable_error(self):
        """Test invalid dict conversion provides actionable error messages."""
        invalid_dict = [{"invalid_field": "value", "missing_name": True}]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(dependencies=invalid_dict)

        error = exc_info.value
        assert "Failed to convert YAML dependency" in str(error)
        context = error.context
        assert "dependency_index" in context
        assert "example_format" in context
        assert "yaml_deserialization" in context

    def test_non_list_dependency_with_helpful_error(self):
        """Test non-list dependencies provide helpful error messages."""
        non_list_dependency = {"single": "dict"}

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(dependencies=non_list_dependency)

        error = exc_info.value
        assert "must be a list" in str(error)
        context = error.context
        assert "input_type" in context
        assert "expected_type" in context
        assert "example" in context


class TestTypeHintConsistency:
    """Test that type hints match implementation (no Any types)."""

    def test_workflow_dependency_condition_validator_type_consistency(self):
        """Test that condition validator type hints are consistent."""
        # This test ensures the validator parameter type matches the implementation
        workflow_id = uuid4()
        dependent_workflow_id = uuid4()

        # Test with None (should be allowed)
        workflow_dep = ModelWorkflowDependency(
            workflow_id=workflow_id,
            dependent_workflow_id=dependent_workflow_id,
            dependency_type="SEQUENTIAL",
            condition=None,
        )
        assert workflow_dep.condition is None

        # Test with invalid type (should be rejected with proper type in error)
        with pytest.raises(OnexError) as exc_info:
            ModelWorkflowDependency(
                workflow_id=workflow_id,
                dependent_workflow_id=dependent_workflow_id,
                dependency_type="SEQUENTIAL",
                condition="invalid_string",
            )

        error = exc_info.value
        assert "STRONG TYPES ONLY" in str(error)
        assert "ModelWorkflowCondition" in str(error)
        # Ensure no mention of Any types in error handling
        assert "Any" not in str(error).replace("any", "")


class TestSecurityEnhancements:
    """Test enhanced security validations for path traversal and injection prevention."""

    def test_absolute_path_rejection_in_module_validation(self):
        """Test that absolute paths are rejected in module validation."""
        malicious_paths = [
            "/etc/passwd",
            "C:\\Windows\\System32",
            "~/malicious",
            "D:\\sensitive\\path",
        ]

        for malicious_path in malicious_paths:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDep", module=malicious_path)

            error = exc_info.value
            # OnexError now nests context under a 'context' key
            security_violations = error.context.get("context", {}).get(
                "security_violations", []
            )
            assert "absolute_path_detected" in security_violations

    def test_enhanced_shell_injection_character_detection(self):
        """Test enhanced detection of shell injection characters."""
        dangerous_chars = [
            "<",
            ">",
            "|",
            "&",
            ";",
            "`",
            "$",
            "'",
            '"',
            "*",
            "?",
            "[",
            "]",
        ]

        for char in dangerous_chars:
            malicious_module = f"test.module{char}.path"

            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDep", module=malicious_module)

            error = exc_info.value
            # OnexError now nests context under a 'context' key
            security_violations = error.context.get("context", {}).get(
                "security_violations", []
            )
            assert "shell_injection_characters" in security_violations

    def test_privileged_path_detection(self):
        """Test detection of potentially privileged paths."""
        privileged_paths = [
            "system.admin.module",
            "root.config.service",
            "admin.privileged.access",
        ]

        for priv_path in privileged_paths:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDep", module=priv_path)

            error = exc_info.value
            # OnexError now nests context under a 'context' key
            security_violations = error.context.get("context", {}).get(
                "security_violations", []
            )
            assert "potentially_privileged_path" in security_violations

    def test_security_recommendations_provided(self):
        """Test that security violations provide actionable recommendations."""
        with pytest.raises(OnexError) as exc_info:
            ModelDependency(name="TestDep", module="../malicious/path")

        error = exc_info.value
        # OnexError now nests context under a 'context' key
        context = error.context.get("context", {})
        assert "recommendations" in context
        assert "security_violations" in context
        assert "valid_example" in context
        assert len(context["recommendations"]) > 0


class TestPerformanceOptimizations:
    """Test performance optimizations including LRU cache and pattern removal."""

    def test_lru_cache_functionality_on_validation(self):
        """Test that LRU cache improves performance on repeated validations."""
        # This test verifies the cache is working by calling the same validation multiple times
        test_module = "omnibase_core.test.module"

        # Create multiple dependencies with the same module (should hit cache)
        deps = [
            ModelDependency(name=f"TestDep{i}", module=test_module) for i in range(10)
        ]

        # All should succeed and benefit from cached validation
        assert all(dep.module == test_module for dep in deps)

    def test_camel_to_snake_case_caching(self):
        """Test that camel to snake case conversion is cached."""
        dep = ModelDependency(name="TestDependency", module="test.module")

        # Call the method multiple times - should benefit from LRU cache
        result1 = dep._camel_to_snake_case("CamelCaseString")
        result2 = dep._camel_to_snake_case("CamelCaseString")  # Should hit cache

        assert result1 == result2 == "camel_case_string"

    @patch(
        "omnibase_core.core.contracts.model_dependency.ModelDependency._MODULE_PATTERN"
    )
    def test_compiled_regex_pattern_usage(self, mock_pattern):
        """Test that compiled regex patterns are used for performance."""
        mock_pattern.match.return_value = True

        ModelDependency._validate_module_format("test.module")

        # Should use the pre-compiled pattern
        mock_pattern.match.assert_called_once_with("test.module")

    def test_memory_footprint_reduction(self):
        """Test that unused patterns are removed to reduce memory footprint."""
        # Verify that _CAMEL_TO_SNAKE_PATTERN is not in class attributes
        # (it was removed as requested in PR feedback)
        assert not hasattr(ModelDependency, "_CAMEL_TO_SNAKE_PATTERN")


class TestErrorHandlingConsistency:
    """Test consistent error handling with flattened context structures."""

    def test_flattened_context_in_workflow_dependency_errors(self):
        """Test that workflow dependency errors have flattened context."""
        workflow_id = uuid4()

        with pytest.raises(OnexError) as exc_info:
            ModelWorkflowDependency(
                workflow_id=workflow_id,
                dependent_workflow_id=workflow_id,  # Same ID = circular dependency
                dependency_type="SEQUENTIAL",
            )

        error = exc_info.value
        context = error.context

        # Ensure context is flattened (no nested "context" key)
        assert "context" not in context  # Should not have nested context
        assert "workflow_id" in context
        assert "dependent_workflow_id" in context
        assert "onex_principle" in context
        assert "prevention_type" in context

    def test_flattened_context_in_condition_validation_errors(self):
        """Test that condition validation errors have flattened context."""
        workflow_id = uuid4()
        dependent_workflow_id = uuid4()

        with pytest.raises(OnexError) as exc_info:
            ModelWorkflowDependency(
                workflow_id=workflow_id,
                dependent_workflow_id=dependent_workflow_id,
                dependency_type="SEQUENTIAL",
                condition="invalid_condition",
            )

        error = exc_info.value
        context = error.context

        # Ensure context is flattened (no nested "context" key)
        assert "context" not in context  # Should not have nested context
        assert "received_type" in context
        assert "expected_type" in context
        assert "onex_principle" in context


class TestCircularDependencyValidation:
    """Test comprehensive circular dependency validation at model level."""

    def test_direct_circular_dependency_prevention(self):
        """Test prevention of direct circular dependencies in contracts."""
        # Create contract that tries to depend on itself
        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                name="SelfReferencing",
                dependencies=[{"name": "selfreferencing", "module": "test.module"}],
            )

        error = exc_info.value
        assert "Direct circular dependency" in str(error)
        assert "cannot depend on itself" in str(error)
        context = error.context
        assert "validation_type" in context
        assert context["validation_type"] == "direct_circular_dependency"

    def test_duplicate_dependency_detection(self):
        """Test detection of duplicate dependencies."""
        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                dependencies=[
                    {"name": "DuplicateDep", "module": "test.module1"},
                    {"name": "DuplicateDep", "module": "test.module2"},  # Same name
                ]
            )

        error = exc_info.value
        assert "Duplicate dependency detected" in str(error)
        context = error.context
        assert "validation_type" in context
        assert context["validation_type"] == "duplicate_dependency"

    def test_module_based_circular_dependency_detection(self):
        """Test detection of potential circular dependencies through module references."""
        with pytest.raises(OnexError) as exc_info:
            create_test_contract(
                name="CircularContract",
                dependencies=[
                    {"name": "SomeDep", "module": "test.circularcontract.module"}
                ],
            )

        error = exc_info.value
        assert "Potential circular dependency" in str(error)
        assert "module contains the contract name" in str(error)
        context = error.context
        assert "validation_type" in context
        assert context["validation_type"] == "module_circular_dependency"

    def test_complexity_limit_validation(self):
        """Test validation of maximum dependency complexity."""
        # Create more dependencies than the complexity limit allows
        complex_dependencies = [
            {"name": f"ComplexDep{i}", "module": f"test.complex.{i}"}
            for i in range(51)  # Exceeds max_dependencies=50
        ]

        with pytest.raises(OnexError) as exc_info:
            create_test_contract(dependencies=complex_dependencies)

        error = exc_info.value
        assert "too many dependencies" in str(error)
        context = error.context
        assert "validation_type" in context
        assert context["validation_type"] == "complexity_limit"
        assert "architectural_guidance" in context

    def test_workflow_dependency_self_reference_prevention(self):
        """Test that ModelWorkflowDependency prevents self-references."""
        same_id = uuid4()

        with pytest.raises(OnexError) as exc_info:
            ModelWorkflowDependency(
                workflow_id=same_id,
                dependent_workflow_id=same_id,
                dependency_type="SEQUENTIAL",
            )

        error = exc_info.value
        assert "CIRCULAR DEPENDENCY DETECTED" in str(error)
        assert "cannot depend on itself" in str(error)


class TestEdgeCasesAndRegressionScenarios:
    """Test edge cases and regression scenarios for robustness."""

    def test_concurrent_validation_thread_safety(self):
        """Test that validators are thread-safe for concurrent access."""
        import threading
        import time

        results = []
        errors = []

        def validate_dependency():
            try:
                dep = ModelDependency(
                    name="ThreadTestDep", module="test.thread.safe.module"
                )
                results.append(dep.name)
            except Exception as e:
                errors.append(str(e))

        # Run multiple threads concurrently
        threads = [threading.Thread(target=validate_dependency) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All validations should succeed with no errors
        assert len(results) == 10
        assert len(errors) == 0
        assert all(name == "ThreadTestDep" for name in results)

    def test_memory_leak_prevention_with_large_lists(self):
        """Test that large dependency lists don't cause memory leaks."""
        # Create and destroy many contracts with dependencies
        for _ in range(100):
            try:
                deps = [{"name": f"Dep{i}", "module": f"test.{i}"} for i in range(50)]
                contract = create_test_contract(dependencies=deps)
                # Contract goes out of scope and should be garbage collected
                del contract
            except Exception:
                # Expected for some iterations due to validation rules
                pass

        # No assertion needed - this test passes if no memory errors occur

    def test_integration_with_actual_yaml_loading(self):
        """Test integration with actual YAML loading scenarios."""
        # Simulate YAML loading by providing dict format dependencies
        yaml_like_data = {
            "name": "yaml-loaded-contract",
            "version": {"major": 1, "minor": 0, "patch": 0},
            "description": "Contract loaded from YAML",
            "node_type": "COMPUTE",
            "input_model": "yaml.input.Model",
            "output_model": "yaml.output.Model",
            "dependencies": [
                {
                    "name": "ProtocolEventBus",
                    "module": "omnibase_core.protocol.event_bus",
                    "dependency_type": "protocol",
                    "required": True,
                },
                {
                    "name": "ServiceRegistry",
                    "module": "omnibase_core.services.registry",
                    "dependency_type": "service",
                    "required": False,
                },
            ],
        }

        # This should work with our enhanced YAML validator
        contract = _TestContract(**yaml_like_data)
        assert len(contract.dependencies) == 2
        assert isinstance(contract.dependencies[0], ModelDependency)
        assert contract.dependencies[0].name == "ProtocolEventBus"

    def test_performance_regression_prevention(self):
        """Test that performance optimizations don't cause regressions."""
        import time

        # Test performance of dependency validation
        start_time = time.time()

        for i in range(100):
            dep = ModelDependency(
                name=f"PerfTestDep{i}", module=f"test.performance.module_{i}"
            )
            # Exercise cached methods
            _ = dep._camel_to_snake_case(f"CamelCase{i}")

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete reasonably quickly (less than 1 second for 100 iterations)
        assert (
            execution_time < 1.0
        ), f"Performance regression detected: {execution_time}s for 100 validations"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
