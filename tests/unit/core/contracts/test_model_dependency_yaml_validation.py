#!/usr/bin/env python3
"""
Test ModelDependency YAML validation and contract loading.

Validates that the new unified dependency model correctly handles
backward compatibility for existing YAML contracts while providing
improved type safety.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.core.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.core.contracts.model_dependency import (
    EnumDependencyType,
    ModelDependency,
    create_dependency,
)
from omnibase_core.enums import EnumNodeType
from omnibase_core.model.core.model_semver import ModelSemVer


class TestModelDependencyYamlValidation:
    """Test YAML validation for ModelDependency and contract loading."""

    def test_create_dependency_from_string(self):
        """Test creating dependency from string format."""
        # Protocol dependency
        dep = create_dependency("ProtocolEventBus")
        assert dep.name == "ProtocolEventBus"
        assert dep.dependency_type == EnumDependencyType.PROTOCOL
        assert dep.module is None

        # Module path dependency
        dep = create_dependency("omnibase.protocol.protocol_consul_client")
        assert dep.name == "protocol_consul_client"
        assert dep.dependency_type == EnumDependencyType.PROTOCOL
        assert dep.module == "omnibase.protocol.protocol_consul_client"

    def test_create_dependency_from_dict(self):
        """Test creating dependency from dictionary format."""
        dep_dict = {
            "name": "event_bus",  # Use name that matches module pattern
            "module": "omnibase.protocol.protocol_event_bus",
            "type": "protocol",
            "version": {
                "major": 1,
                "minor": 0,
                "patch": 0,
            },  # Proper ModelSemVer format
            "required": True,
        }

        dep = create_dependency(dep_dict)
        assert dep.name == "event_bus"
        assert dep.dependency_type == EnumDependencyType.PROTOCOL
        assert dep.module == "omnibase.protocol.protocol_event_bus"
        assert dep.version == ModelSemVer(major=1, minor=0, patch=0)
        assert dep.required is True

    def test_create_dependency_from_structured_object(self):
        """Test creating dependency from structured object."""

        class MockStructuredDep:
            def __init__(self):
                self.name = "logger"  # Use name that matches module pattern
                self.type = "protocol"
                self.module = "omnibase.protocol.protocol_logger"
                self.version = {
                    "major": 2,
                    "minor": 0,
                    "patch": 0,
                }  # Proper ModelSemVer format

        structured_dep = MockStructuredDep()
        dep = create_dependency(structured_dep)
        assert dep.name == "logger"
        assert dep.dependency_type == EnumDependencyType.PROTOCOL
        assert dep.module == "omnibase.protocol.protocol_logger"
        assert dep.version == ModelSemVer(major=2, minor=0, patch=0)

    def test_model_dependency_validation(self):
        """Test ModelDependency validation rules."""
        # Valid dependency
        dep = ModelDependency(
            name="ProtocolEventBus", dependency_type=EnumDependencyType.PROTOCOL
        )
        assert dep.matches_onex_patterns() is True

        # Invalid empty name
        with pytest.raises(
            ValidationError, match="String should have at least 1 character"
        ):
            ModelDependency(name="", dependency_type=EnumDependencyType.PROTOCOL)

    def test_yaml_contract_loading_string_dependencies(self):
        """Test loading contract from YAML with string dependencies."""
        # Create minimal valid contract data
        contract_data = {
            "name": "TestOrchestratorContract",
            "version": {"major": 1, "minor": 0, "patch": 0},
            "description": "Test orchestrator contract with string dependencies",
            "node_type": "ORCHESTRATOR",
            "input_model": "TestInputModel",
            "output_model": "TestOutputModel",
            "node_name": "test_orchestrator",
            "main_tool_class": "TestTool",
            "dependencies": [
                "ProtocolEventBus",
                "ProtocolLogger",
                "omnibase.protocol.protocol_consul_client",
            ],
            "thunk_emission_config": {
                "max_parallel_thunks": 10,
                "thunk_timeout_seconds": 30,
            },
            "performance": {"single_operation_max_ms": 1000},
            "workflow_registry": {
                "default_workflow_id": "test_workflow",
                "workflows": {
                    "test_workflow": {
                        "workflow_id": "test_workflow",
                        "workflow_name": "Test Workflow",
                        "workflow_type": "sequential",
                        "steps": [
                            {
                                "step_id": "step1",
                                "step_type": "compute",
                                "step_name": "Test Step",
                            }
                        ],
                    }
                },
            },
        }

        contract = ModelContractOrchestrator(**contract_data)

        # Verify dependencies were converted to ModelDependency objects
        assert len(contract.dependencies) == 3

        # Check first dependency (simple Protocol name)
        dep1 = contract.dependencies[0]
        assert isinstance(dep1, ModelDependency)
        assert dep1.name == "ProtocolEventBus"
        assert dep1.dependency_type == EnumDependencyType.PROTOCOL

        # Check second dependency
        dep2 = contract.dependencies[1]
        assert isinstance(dep2, ModelDependency)
        assert dep2.name == "ProtocolLogger"

        # Check third dependency (module path)
        dep3 = contract.dependencies[2]
        assert isinstance(dep3, ModelDependency)
        assert dep3.name == "protocol_consul_client"
        assert dep3.module == "omnibase.protocol.protocol_consul_client"

    def test_dependencies_validator_conversion(self):
        """Test that the field validator converts various formats correctly."""
        # Test direct instantiation with mixed dependency formats
        from omnibase_core.core.contracts.model_contract_base import ModelContractBase

        # Test that the validator converts string dependencies
        test_deps = ["ProtocolEventBus", "omnibase.protocol.protocol_logger"]
        converted = ModelContractBase.convert_dependencies_to_model_dependency(
            test_deps
        )

        assert len(converted) == 2
        assert all(isinstance(dep, ModelDependency) for dep in converted)
        assert converted[0].name == "ProtocolEventBus"
        assert converted[1].name == "protocol_logger"

    def test_dependency_serialization_round_trip(self):
        """Test that dependencies can be serialized and deserialized correctly."""
        original_dep = ModelDependency(
            name="event_bus",  # Use name that matches module
            module="omnibase.protocol.protocol_event_bus",
            dependency_type=EnumDependencyType.PROTOCOL,
            version=ModelSemVer(major=1, minor=0, patch=0),
            required=True,
            description="Event bus protocol for async communication",
        )

        # Serialize to dict
        dep_dict = original_dep.to_dict()
        assert dep_dict.get("name") == "event_bus"
        assert dep_dict.get("type") == "protocol"
        assert dep_dict.get("version") == {"major": 1, "minor": 0, "patch": 0}

        # Create new dependency from dict
        restored_dep = create_dependency(dep_dict)
        assert restored_dep.name == original_dep.name
        assert restored_dep.module == original_dep.module
        assert restored_dep.dependency_type == original_dep.dependency_type
        assert restored_dep.version == original_dep.version
        assert restored_dep.required == original_dep.required
        assert restored_dep.description == original_dep.description

    def test_invalid_dependency_formats(self):
        """Test error handling for invalid dependency formats."""
        # Invalid empty string
        with pytest.raises(ValueError, match="Dependency string cannot be empty"):
            create_dependency("")

        # Invalid dict without name
        with pytest.raises(ValueError, match="Dependency dict must contain 'name'"):
            create_dependency({"type": "protocol"})

        # Invalid structured object without name
        class InvalidStructuredDep:
            def __init__(self):
                self.type = "protocol"

        with pytest.raises(ValueError, match="Structured dependency must have 'name'"):
            create_dependency(InvalidStructuredDep())

    def test_string_versions_rejected(self):
        """Test that string versions are properly rejected."""
        # String version in dict format should be rejected
        with pytest.raises(TypeError, match="String versions not allowed: '1.0.0'"):
            create_dependency(
                {"name": "test_dep", "version": "1.0.0"}  # This should be rejected
            )

        # String version in structured object should be rejected
        class StructuredDepWithStringVersion:
            def __init__(self):
                self.name = "test_dep"
                self.version = "2.0.0"  # This should be rejected

        with pytest.raises(TypeError, match="String versions not allowed: '2.0.0'"):
            create_dependency(StructuredDepWithStringVersion())

    def test_onex_pattern_validation(self):
        """Test ONEX naming pattern validation."""
        # Valid protocol patterns
        valid_deps = [
            ModelDependency(
                name="ProtocolEventBus", dependency_type=EnumDependencyType.PROTOCOL
            ),
            ModelDependency(
                name="event_protocol", dependency_type=EnumDependencyType.PROTOCOL
            ),
            ModelDependency(
                name="logger",
                module="omnibase.protocol.protocol_logger",
                dependency_type=EnumDependencyType.PROTOCOL,
            ),
        ]

        for dep in valid_deps:
            assert dep.matches_onex_patterns() is True, f"Failed for {dep.name}"

        # Service and module types should also be valid (more flexible patterns)
        service_dep = ModelDependency(
            name="CustomService", dependency_type=EnumDependencyType.SERVICE
        )
        assert service_dep.matches_onex_patterns() is True

        module_dep = ModelDependency(
            name="utility_module", dependency_type=EnumDependencyType.MODULE
        )
        assert module_dep.matches_onex_patterns() is True
