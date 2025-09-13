#!/usr/bin/env python3
"""
Comprehensive edge case tests for ModelWorkflowDependency validation.

Tests validation scenarios, error handling, and ONEX compliance for workflow dependencies.
Updated for Phase 3L: Added UUID validation tests for workflow_id strong typing enforcement.
"""

import uuid

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
        """Test successful creation of valid workflow dependency with UUID."""
        workflow_uuid = uuid.uuid4()
        dependency = ModelWorkflowDependency(
            workflow_id=workflow_uuid,
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            required=True,
            timeout_ms=5000,
            description="Process documents before analysis",
        )

        assert dependency.workflow_id == workflow_uuid
        assert dependency.dependency_type == EnumWorkflowDependencyType.SEQUENTIAL
        assert dependency.required is True
        assert dependency.timeout_ms == 5000
        assert dependency.is_sequential() is True
        assert dependency.is_parallel() is False

    def test_workflow_id_uuid_validation_success(self):
        """Test successful workflow ID UUID validation."""
        valid_uuids = [
            uuid.uuid4(),
            uuid.UUID("12345678-1234-5678-9abc-123456789012"),  # Fixed UUID
            uuid.UUID(int=0),  # Minimum UUID
            uuid.uuid1(),  # Time-based UUID
            uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),  # Max UUID
        ]

        for workflow_uuid in valid_uuids:
            dependency = ModelWorkflowDependency(
                workflow_id=workflow_uuid,
                dependency_type=EnumWorkflowDependencyType.PARALLEL,
            )
            assert dependency.workflow_id == workflow_uuid

    def test_workflow_id_invalid_type_validation_failure(self):
        """Test workflow ID invalid type validation failures."""
        invalid_ids = ["not-a-uuid", 123, [], {}, ""]

        for workflow_id in invalid_ids:
            with pytest.raises(ValidationError):
                ModelWorkflowDependency(
                    workflow_id=workflow_id,
                    dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
                )

    def test_workflow_id_string_to_uuid_conversion(self):
        """Test that valid UUID strings can be converted to UUID objects."""
        # Test string UUID conversion
        uuid_string = "12345678-1234-5678-9abc-123456789012"
        expected_uuid = uuid.UUID(uuid_string)

        dependency = ModelWorkflowDependency(
            workflow_id=uuid_string,  # Should be converted to UUID
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
        )

        assert dependency.workflow_id == expected_uuid
        assert isinstance(dependency.workflow_id, uuid.UUID)

    def test_workflow_id_none_validation_failure(self):
        """Test workflow ID None validation failure."""
        with pytest.raises(ValidationError):
            ModelWorkflowDependency(
                workflow_id=None,
                dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            )

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
                workflow_id=uuid.uuid4(),
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
                    workflow_id=uuid.uuid4(),
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
                workflow_id=uuid.uuid4(),
                dependency_type=EnumWorkflowDependencyType.CONDITIONAL,
                condition=condition,
            )
            assert dependency.condition is None

    def test_condition_none_handling(self):
        """Test None condition is handled correctly."""
        dependency = ModelWorkflowDependency(
            workflow_id=uuid.uuid4(),
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            condition=None,
        )
        assert dependency.condition is None

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        dependency = ModelWorkflowDependency(
            workflow_id=uuid.uuid4(),
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            timeout_ms=1000,
        )
        assert dependency.timeout_ms == 1000

        # Invalid timeout (less than 1)
        with pytest.raises(ValidationError):
            ModelWorkflowDependency(
                workflow_id=uuid.uuid4(),
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
                workflow_id=uuid.uuid4(), dependency_type=dep_type
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
            workflow_id=uuid.uuid4(),
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            required=False,
            condition="status == 'ready'",
            timeout_ms=30000,
            version_constraint=version,
            description="Test dependency",
        )

        result_dict = dependency.model_dump(mode="json", exclude_none=True)

        # Check required fields - workflow_id will be serialized as string
        assert result_dict["workflow_id"] == str(dependency.workflow_id)
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
            workflow_id=uuid.uuid4(),
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
        assert result_dict["workflow_id"] == str(dependency.workflow_id)
        assert result_dict["dependency_type"] == "parallel"

    def test_whitespace_stripping(self):
        """Test that whitespace is properly stripped from string fields."""
        test_uuid = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        dependency = ModelWorkflowDependency(
            workflow_id=test_uuid,
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            condition="  status == 'ready'  ",
            description="  Test description  ",
        )

        # Workflow ID should remain as UUID
        assert dependency.workflow_id == test_uuid

        # Condition should be stripped due to validator
        assert dependency.condition == "status == 'ready'"

        # Description should be stripped due to model config
        assert dependency.description == "Test description"

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per model config."""
        # This should not raise an error due to extra="ignore"
        test_uuid = uuid.uuid4()
        dependency = ModelWorkflowDependency(
            workflow_id=test_uuid,
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
            extra_field="should be ignored",
            another_extra=123,
        )

        assert dependency.workflow_id == test_uuid
        assert not hasattr(dependency, "extra_field")
        assert not hasattr(dependency, "another_extra")

    def test_circular_dependency_detection_context(self):
        """Test context information is available for circular dependency detection."""
        # This tests that we have the necessary context for future circular dependency detection
        test_uuid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        dependency = ModelWorkflowDependency(
            workflow_id=test_uuid,
            dependency_type=EnumWorkflowDependencyType.SEQUENTIAL,
        )

        # Ensure we can create a dependency chain representation
        chain_info = {
            "current_workflow": dependency.workflow_id,
            "dependency_type": dependency.dependency_type.value,  # Access enum value properly
            "is_required": dependency.required,
        }

        assert chain_info["current_workflow"] == test_uuid
        assert chain_info["dependency_type"] == "sequential"
        assert chain_info["is_required"] is True


class TestModelWorkflowDependencyIntegration:
    """Integration tests for workflow dependency scenarios."""

    def test_yaml_serialization_compatibility(self):
        """Test that dependencies can be serialized/deserialized for YAML storage."""
        import json

        test_uuid = uuid.UUID("11111111-2222-3333-4444-555555555555")
        dependency = ModelWorkflowDependency(
            workflow_id=test_uuid,
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

        # Verify we can reconstruct (UUID will be serialized as string in JSON)
        reconstructed = ModelWorkflowDependency(
            workflow_id=uuid.UUID(
                parsed_data["workflow_id"]
            ),  # Convert string back to UUID
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

    def test_yaml_deserialization_comprehensive(self):
        """Test comprehensive YAML deserialization for workflow dependencies."""
        import yaml

        # Create test YAML data with UUID
        yaml_data = """
        workflow_id: "99999999-8888-7777-6666-555555555555"
        dependency_type: "sequential"
        required: true
        condition: "status == 'completed'"
        timeout_ms: 30000
        description: "YAML test dependency"
        """

        # Parse YAML
        parsed_yaml = yaml.safe_load(yaml_data)

        # Create dependency from YAML data
        dependency = ModelWorkflowDependency(
            workflow_id=uuid.UUID(parsed_yaml["workflow_id"]),
            dependency_type=EnumWorkflowDependencyType(parsed_yaml["dependency_type"]),
            required=parsed_yaml["required"],
            condition=parsed_yaml["condition"],
            timeout_ms=parsed_yaml["timeout_ms"],
            description=parsed_yaml["description"],
        )

        # Verify all fields
        assert dependency.workflow_id == uuid.UUID(
            "99999999-8888-7777-6666-555555555555"
        )
        assert dependency.dependency_type == EnumWorkflowDependencyType.SEQUENTIAL
        assert dependency.required is True
        assert dependency.condition == "status == 'completed'"
        assert dependency.timeout_ms == 30000
        assert dependency.description == "YAML test dependency"

    def test_yaml_round_trip_serialization(self):
        """Test YAML round-trip serialization/deserialization."""
        import yaml

        # Create original dependency
        original_uuid = uuid.uuid4()
        original = ModelWorkflowDependency(
            workflow_id=original_uuid,
            dependency_type=EnumWorkflowDependencyType.PARALLEL,
            required=False,
            timeout_ms=25000,
            description="Round-trip test",
        )

        # Serialize to dict (YAML-compatible)
        data = original.model_dump(mode="json", exclude_none=True)

        # Convert to YAML and back
        yaml_str = yaml.dump(data)
        parsed_yaml = yaml.safe_load(yaml_str)

        # Reconstruct from YAML
        reconstructed = ModelWorkflowDependency(
            workflow_id=uuid.UUID(parsed_yaml["workflow_id"]),
            dependency_type=EnumWorkflowDependencyType(parsed_yaml["dependency_type"]),
            required=parsed_yaml["required"],
            timeout_ms=parsed_yaml["timeout_ms"],
            description=parsed_yaml["description"],
        )

        # Verify round-trip integrity
        assert reconstructed.workflow_id == original.workflow_id
        assert reconstructed.dependency_type == original.dependency_type
        assert reconstructed.required == original.required
        assert reconstructed.timeout_ms == original.timeout_ms
        assert reconstructed.description == original.description
