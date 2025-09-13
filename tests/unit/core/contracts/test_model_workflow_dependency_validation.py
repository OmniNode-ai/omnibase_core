#!/usr/bin/env python3
"""
Comprehensive edge case tests for ModelWorkflowDependency validation.

Tests validation scenarios, error handling, and ONEX compliance for workflow dependencies.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.core.contracts.model_workflow_dependency import (
    ModelWorkflowDependency,
)
from omnibase_core.core.errors.core_errors import OnexError
from omnibase_core.enums.enum_workflow_dependency_type import EnumWorkflowDependencyType


class TestModelWorkflowDependencyValidation:
    """Test comprehensive validation scenarios for ModelWorkflowDependency."""

    def test_valid_workflow_dependency_creation(self):
        """Test successful creation of valid workflow dependency."""
        dependency = ModelWorkflowDependency(
            workflow_id="document-processing",
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            required=True,
            timeout_ms=5000,
            description="Process documents before analysis",
        )

        assert dependency.workflow_id == "document-processing"
        assert dependency.dependency_type == EnumWorkflowDependencyType.SEQUENTIAL
        assert dependency.required is True
        assert dependency.timeout_ms == 5000
        assert dependency.is_sequential() is True
        assert dependency.is_parallel() is False

    def test_workflow_id_format_validation_success(self):
        """Test successful workflow ID format validation."""
        valid_ids = [
            "abc",
            "workflow-123",
            "data-processing-pipeline",
            "ml-model-training",
            "user-auth-validation",
            "ab",  # minimum length
            "a" * 64,  # maximum length
        ]

        for workflow_id in valid_ids:
            dependency = ModelWorkflowDependency(
                workflow_id=workflow_id,
                dependency_type=EnumWorkflowDependencyType.PARALLEL,
            )
            assert dependency.workflow_id == workflow_id

    def test_workflow_id_empty_validation_failure(self):
        """Test workflow ID empty/whitespace validation failures."""
        invalid_ids = ["", "   ", "\t", "\n", None]

        for workflow_id in invalid_ids:
            with pytest.raises(OnexError) as exc_info:
                ModelWorkflowDependency(
                    workflow_id=workflow_id,
                    dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
                )

            error = exc_info.value
            assert "cannot be empty or whitespace-only" in error.message
            assert error.context["context"]["workflow_id"] == workflow_id

    def test_workflow_id_length_validation_failures(self):
        """Test workflow ID length validation failures."""
        # Too short
        with pytest.raises(OnexError) as exc_info:
            ModelWorkflowDependency(
                workflow_id="a", dependency_type=EnumWorkflowDependencyType.SEQUENTIAL
            )

        error = exc_info.value
        assert "too short" in error.message
        assert error.context["context"]["length"] == 1
        assert error.context["context"]["min_length"] == 2

        # Too long
        long_id = "a" * 65
        with pytest.raises(OnexError) as exc_info:
            ModelWorkflowDependency(
                workflow_id=long_id,
                dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            )

        error = exc_info.value
        assert "too long" in error.message
        assert error.context["context"]["length"] == 65
        assert error.context["context"]["max_length"] == 64

    def test_workflow_id_format_validation_failures(self):
        """Test workflow ID format validation failures."""
        invalid_formats = [
            "UPPERCASE",  # uppercase not allowed
            "mixed-Case",  # mixed case not allowed
            "has_underscore",  # underscore not allowed
            "has spaces",  # spaces not allowed
            "has--double-hyphens",  # consecutive hyphens not allowed
            "-starts-with-hyphen",  # leading hyphen not allowed
            "ends-with-hyphen-",  # trailing hyphen not allowed
            "has.dot",  # dot not allowed
            "has@symbol",  # special characters not allowed
            "has/slash",  # slash not allowed
        ]

        for workflow_id in invalid_formats:
            with pytest.raises(OnexError) as exc_info:
                ModelWorkflowDependency(
                    workflow_id=workflow_id,
                    dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
                )

            error = exc_info.value
            assert "Invalid workflow ID format" in error.message
            assert error.context["context"]["workflow_id"] == workflow_id
            assert "expected_format" in error.context["context"]

    def test_condition_validation_success(self):
        """Test successful condition validation."""
        valid_conditions = [
            "status == 'completed'",
            "result.success == true",
            "output_count > 0",
            "workflow.stage in ['production', 'staging']",
            "abc",  # minimum length
        ]

        for condition in valid_conditions:
            dependency = ModelWorkflowDependency(
                workflow_id="test-workflow",
                dependency_type=EnumWorkflowDependencyType.CONDITIONAL,
                condition=condition,
            )
            assert dependency.condition == condition

    def test_condition_validation_failure(self):
        """Test condition validation failures."""
        invalid_conditions = [
            "a",  # too short
            "ab",  # too short
        ]

        for condition in invalid_conditions:
            with pytest.raises(OnexError) as exc_info:
                ModelWorkflowDependency(
                    workflow_id="test-workflow",
                    dependency_type=EnumWorkflowDependencyType.CONDITIONAL,
                    condition=condition,
                )

            error = exc_info.value
            assert "too short" in error.message
            assert error.context["context"]["condition"] == condition.strip()
            assert error.context["context"]["min_length"] == 3

    def test_condition_empty_becomes_none(self):
        """Test that empty/whitespace conditions become None (valid behavior)."""
        empty_conditions = ["", "   ", "\t", "\n"]

        for condition in empty_conditions:
            dependency = ModelWorkflowDependency(
                workflow_id="test-workflow",
                dependency_type=EnumWorkflowDependencyType.CONDITIONAL,
                condition=condition,
            )
            assert dependency.condition is None

    def test_condition_none_handling(self):
        """Test None condition is handled correctly."""
        dependency = ModelWorkflowDependency(
            workflow_id="test-workflow",
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            condition=None,
        )
        assert dependency.condition is None

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        dependency = ModelWorkflowDependency(
            workflow_id="test-workflow",
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            timeout_ms=1000,
        )
        assert dependency.timeout_ms == 1000

        # Invalid timeout (less than 1)
        with pytest.raises(ValidationError):
            ModelWorkflowDependency(
                workflow_id="test-workflow",
                dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
                timeout_ms=0,
            )

    def test_dependency_type_methods(self):
        """Test dependency type helper methods."""
        # Test each dependency type
        test_cases = [
            (EnumWorkflowDependencyType.SEQUENTIAL, "is_sequential"),
            (EnumWorkflowDependencyType.PARALLEL, "is_parallel"),
            (EnumWorkflowDependencyType.CONDITIONAL, "is_conditional"),
            (EnumWorkflowDependencyType.BLOCKING, "is_blocking"),
            (EnumWorkflowDependencyType.COMPENSATING, "is_compensating"),
        ]

        for dep_type, method_name in test_cases:
            dependency = ModelWorkflowDependency(
                workflow_id="test-workflow", dependency_type=dep_type
            )

            # Check that the correct method returns True
            assert getattr(dependency, method_name)() is True

            # Check that other methods return False
            for other_dep_type, other_method in test_cases:
                if other_method != method_name:
                    assert getattr(dependency, other_method)() is False

    def test_to_dict_conversion(self):
        """Test dictionary conversion with all fields."""
        from omnibase_core.models.core.model_semver import ModelSemVer

        version = ModelSemVer(major=1, minor=2, patch=3)
        dependency = ModelWorkflowDependency(
            workflow_id="test-workflow",
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            required=False,
            condition="status == 'ready'",
            timeout_ms=30000,
            version_constraint=version,
            description="Test dependency",
        )

        result_dict = dependency.model_dump(mode="json", exclude_none=True)

        # Check required fields
        assert result_dict["workflow_id"] == "test-workflow"
        assert (
            result_dict["dependency_type"] == "sequential"
        )  # Enum serialized as string

        # Check optional fields
        assert result_dict["required"] is False
        assert result_dict["condition"] == "status == 'ready'"
        assert result_dict["timeout_ms"] == 30000
        assert result_dict["description"] == "Test dependency"
        assert "version_constraint" in result_dict

    def test_to_dict_minimal(self):
        """Test dictionary conversion with minimal required fields."""
        dependency = ModelWorkflowDependency(
            workflow_id="minimal-workflow",
            dependency_type=EnumWorkflowDependencyType.PARALLEL,
        )

        result_dict = dependency.model_dump(mode="json", exclude_none=True)

        # Should only have required fields
        expected_keys = {
            "workflow_id",
            "dependency_type",
            "required",
        }  # required has default True
        assert set(result_dict.keys()) == expected_keys
        assert result_dict["workflow_id"] == "minimal-workflow"
        assert result_dict["dependency_type"] == "parallel"

    def test_whitespace_stripping(self):
        """Test that whitespace is properly stripped from string fields."""
        dependency = ModelWorkflowDependency(
            workflow_id="  test-workflow  ",
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            condition="  status == 'ready'  ",
            description="  Test description  ",
        )

        # Workflow ID should be stripped due to validator
        assert dependency.workflow_id == "test-workflow"

        # Condition should be stripped due to validator
        assert dependency.condition == "status == 'ready'"

        # Description should be stripped due to model config
        assert dependency.description == "Test description"

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per model config."""
        # This should not raise an error due to extra="ignore"
        dependency = ModelWorkflowDependency(
            workflow_id="test-workflow",
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            extra_field="should be ignored",
            another_extra=123,
        )

        assert dependency.workflow_id == "test-workflow"
        assert not hasattr(dependency, "extra_field")
        assert not hasattr(dependency, "another_extra")

    def test_circular_dependency_detection_context(self):
        """Test context information is available for circular dependency detection."""
        # This tests that we have the necessary context for future circular dependency detection
        dependency = ModelWorkflowDependency(
            workflow_id="workflow-a",
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
        )

        # Ensure we can create a dependency chain representation
        chain_info = {
            "current_workflow": dependency.workflow_id,
            "dependency_type": dependency.dependency_type.value,  # Access enum value properly
            "is_required": dependency.required,
        }

        assert chain_info["current_workflow"] == "workflow-a"
        assert chain_info["dependency_type"] == "sequential"
        assert chain_info["is_required"] is True


class TestModelWorkflowDependencyIntegration:
    """Integration tests for workflow dependency scenarios."""

    def test_yaml_serialization_compatibility(self):
        """Test that dependencies can be serialized/deserialized for YAML storage."""
        import json

        dependency = ModelWorkflowDependency(
            workflow_id="serialization-test",
            dependency_type=EnumWorkflowDependencyType.PARALLEL,
            required=False,
            timeout_ms=15000,
            description="Test serialization",
        )

        # Convert to dict (YAML-compatible)
        data = dependency.model_dump(mode="json", exclude_none=True)

        # Simulate JSON serialization (similar to YAML)
        json_str = json.dumps(data)
        parsed_data = json.loads(json_str)

        # Verify we can reconstruct
        reconstructed = ModelWorkflowDependency(
            workflow_id=parsed_data["workflow_id"],
            dependency_type=EnumWorkflowDependencyType(
                parsed_data["dependency_type"]
            ),  # Use proper Pydantic field name
            required=parsed_data["required"],
            timeout_ms=parsed_data["timeout_ms"],
            description=parsed_data["description"],
        )

        assert reconstructed.workflow_id == dependency.workflow_id
        assert reconstructed.dependency_type == dependency.dependency_type
        assert reconstructed.required == dependency.required
        assert reconstructed.timeout_ms == dependency.timeout_ms
        assert reconstructed.description == dependency.description
