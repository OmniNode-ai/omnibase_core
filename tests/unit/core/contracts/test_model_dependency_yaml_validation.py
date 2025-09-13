#!/usr/bin/env python3
"""
Test ModelDependency YAML validation and contract loading.

Validates that the new unified dependency model correctly handles
existing YAML contracts with improved type safety and proper validation.
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
)
from omnibase_core.enums import EnumNodeType
from omnibase_core.models.core.model_semver import ModelSemVer


class TestModelDependencyYamlValidation:
    """Test YAML validation for ModelDependency and contract loading."""

    @staticmethod
    def _create_dependency_from_string(dependency_str: str) -> ModelDependency:
        """
        ONEX-compliant helper to create ModelDependency from string.
        Uses proper Pydantic model instantiation instead of factory methods.
        """
        if not dependency_str or not dependency_str.strip():
            raise ValueError("Dependency string cannot be empty")

        dependency_str = dependency_str.strip()

        # Handle fully qualified module paths
        if "." in dependency_str:
            parts = dependency_str.split(".")
            name = parts[-1]  # Last part is the name
            module = dependency_str
            # Infer type from module path (protocols contain 'protocol')
            dependency_type = (
                EnumDependencyType.PROTOCOL
                if "protocol" in module.lower()
                else EnumDependencyType.MODULE
            )
        else:
            # Simple name format
            name = dependency_str
            module = None
            # Infer type from name (protocols typically contain 'Protocol' or 'protocol')
            dependency_type = (
                EnumDependencyType.PROTOCOL
                if "protocol" in name.lower()
                else EnumDependencyType.SERVICE
            )

        return ModelDependency(
            name=name,
            module=module,
            dependency_type=dependency_type,
        )

    @staticmethod
    def _create_dependency_from_dict(
        dependency_dict: Dict[str, Any],
    ) -> ModelDependency:
        """
        ONEX-compliant helper to create ModelDependency from dict.
        Uses model_validate instead of factory methods.
        """
        if not isinstance(dependency_dict, dict):
            raise ValueError(f"Expected dict, got {type(dependency_dict)}")

        if "name" not in dependency_dict:
            raise ValueError("Dependency dict must contain 'name' field")

        # Convert "type" field to "dependency_type" for Pydantic model
        processed_dict = dependency_dict.copy()
        if "type" in processed_dict:
            processed_dict["dependency_type"] = processed_dict.pop("type")

        # Reject string versions - enforce ModelSemVer
        if "version" in processed_dict and isinstance(processed_dict["version"], str):
            raise TypeError(
                f"String versions not allowed: '{processed_dict['version']}'"
            )

        # Convert version dict to ModelSemVer if needed
        if "version" in processed_dict and isinstance(processed_dict["version"], dict):
            version_dict = processed_dict["version"]
            processed_dict["version"] = ModelSemVer(**version_dict)

        return ModelDependency.model_validate(processed_dict)

    @staticmethod
    def _create_dependency_from_structured(structured_dep: Any) -> ModelDependency:
        """
        ONEX-compliant helper to create ModelDependency from structured object.
        Uses proper attribute extraction and model instantiation.
        """
        if not hasattr(structured_dep, "name"):
            raise ValueError("Structured dependency must have 'name' attribute")

        # Extract attributes
        data = {"name": structured_dep.name}

        if hasattr(structured_dep, "module"):
            data["module"] = structured_dep.module

        if hasattr(structured_dep, "type"):
            data["dependency_type"] = structured_dep.type

        if hasattr(structured_dep, "version"):
            version = structured_dep.version
            # Reject string versions - enforce ModelSemVer
            if isinstance(version, str):
                raise TypeError(f"String versions not allowed: '{version}'")
            if isinstance(version, dict):
                data["version"] = ModelSemVer(**version)
            else:
                data["version"] = version

        if hasattr(structured_dep, "required"):
            data["required"] = structured_dep.required

        if hasattr(structured_dep, "description"):
            data["description"] = structured_dep.description

        return ModelDependency.model_validate(data)

    def test_create_dependency_from_string(self):
        """Test creating dependency from string format."""
        # Protocol dependency
        dep = self._create_dependency_from_string("ProtocolEventBus")
        assert dep.name == "ProtocolEventBus"
        assert dep.dependency_type == EnumDependencyType.PROTOCOL
        assert dep.module is None

        # Module path dependency
        dep = self._create_dependency_from_string(
            "omnibase.protocol.protocol_consul_client"
        )
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

        dep = self._create_dependency_from_dict(dep_dict)
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
        dep = self._create_dependency_from_structured(structured_dep)
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

    def test_yaml_contract_loading_structured_dependencies(self):
        """Test loading contract from YAML with ONEX-compliant structured dependencies."""
        # Create minimal valid contract data
        contract_data = {
            "name": "TestOrchestratorContract",
            "version": {"major": 1, "minor": 0, "patch": 0},
            "description": "Test orchestrator contract with ONEX-compliant structured dependencies",
            "node_type": "ORCHESTRATOR",
            "input_model": "TestInputModel",
            "output_model": "TestOutputModel",
            "node_name": "test_orchestrator",
            "main_tool_class": "TestTool",
            "dependencies": [
                {"name": "ProtocolEventBus", "type": "protocol"},
                {"name": "ProtocolLogger", "type": "protocol"},
                {
                    "name": "protocol_consul_client",
                    "module": "omnibase.protocol.protocol_consul_client",
                    "type": "protocol",
                },
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

        # Check first dependency (structured protocol dict)
        dep1 = contract.dependencies[0]
        assert isinstance(dep1, ModelDependency)
        assert dep1.name == "ProtocolEventBus"
        assert dep1.dependency_type == EnumDependencyType.PROTOCOL

        # Check second dependency (structured protocol dict)
        dep2 = contract.dependencies[1]
        assert isinstance(dep2, ModelDependency)
        assert dep2.name == "ProtocolLogger"
        assert dep2.dependency_type == EnumDependencyType.PROTOCOL

        # Check third dependency (structured dict with module path)
        dep3 = contract.dependencies[2]
        assert isinstance(dep3, ModelDependency)
        assert dep3.name == "protocol_consul_client"
        assert dep3.module == "omnibase.protocol.protocol_consul_client"
        assert dep3.dependency_type == EnumDependencyType.PROTOCOL

    def test_dependencies_validator_conversion(self):
        """Test that the dependency conversion works correctly with ONEX patterns."""
        # Test converting string dependencies using ONEX-compliant helpers
        test_deps = ["ProtocolEventBus", "omnibase.protocol.protocol_logger"]
        converted = [self._create_dependency_from_string(dep) for dep in test_deps]

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
        restored_dep = self._create_dependency_from_dict(dep_dict)
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
            self._create_dependency_from_string("")

        # Invalid dict without name
        with pytest.raises(ValueError, match="Dependency dict must contain 'name'"):
            self._create_dependency_from_dict({"type": "protocol"})

        # Invalid structured object without name
        class InvalidStructuredDep:
            def __init__(self):
                self.type = "protocol"

        with pytest.raises(ValueError, match="Structured dependency must have 'name'"):
            self._create_dependency_from_structured(InvalidStructuredDep())

    def test_string_versions_rejected(self):
        """Test that string versions are properly rejected."""
        # String version in dict format should be rejected
        with pytest.raises(TypeError, match="String versions not allowed: '1.0.0'"):
            self._create_dependency_from_dict(
                {"name": "test_dep", "version": "1.0.0"}  # This should be rejected
            )

        # String version in structured object should be rejected
        class StructuredDepWithStringVersion:
            def __init__(self):
                self.name = "test_dep"
                self.version = "2.0.0"  # This should be rejected

        with pytest.raises(TypeError, match="String versions not allowed: '2.0.0'"):
            self._create_dependency_from_structured(StructuredDepWithStringVersion())

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

    def test_camel_to_snake_case_conversion(self):
        """Test camelCase to snake_case conversion helper."""
        dep = ModelDependency(
            name="TestDependency", dependency_type=EnumDependencyType.PROTOCOL
        )

        # Test various camelCase patterns - updated to match actual regex behavior
        assert dep._camel_to_snake_case("eventBus") == "event_bus"
        assert (
            dep._camel_to_snake_case("EventBus") == "event_bus"
        )  # Leading cap becomes lowercase
        assert dep._camel_to_snake_case("XMLParser") == "xmlparser"  # Consecutive caps
        assert dep._camel_to_snake_case("simple") == "simple"  # No caps
        assert (
            dep._camel_to_snake_case("HTTPClient") == "httpclient"
        )  # Consecutive caps
        assert (
            dep._camel_to_snake_case("parseXMLData") == "parse_xmldata"
        )  # Mixed pattern

    def test_module_path_validation_with_hyphens(self):
        """Test that module paths with hyphens are accepted."""
        # Should accept hyphens in module paths
        dep_with_hyphens = ModelDependency(
            name="test_dep",
            module="my-package.sub-module.protocol_service",
            dependency_type=EnumDependencyType.PROTOCOL,
        )
        assert dep_with_hyphens.module == "my-package.sub-module.protocol_service"

    def test_consistency_validation_improvements(self):
        """Test improved consistency validation logic."""
        # Protocol with proper snake_case matching
        protocol_dep = ModelDependency(
            name="ProtocolEventBus",
            module="omnibase.protocol.protocol_event_bus",
            dependency_type=EnumDependencyType.PROTOCOL,
        )
        # Should validate without errors
        assert protocol_dep.name == "ProtocolEventBus"

        # Service type should be flexible
        service_dep = ModelDependency(
            name="CustomService",
            module="different.path.implementation",
            dependency_type=EnumDependencyType.SERVICE,
        )
        # Should validate without errors due to service flexibility
        assert service_dep.name == "CustomService"

    def test_performance_with_multiple_dependencies(self):
        """Test performance characteristics with multiple dependencies."""
        import time

        # Test creating many dependencies
        start_time = time.time()

        dependencies = []
        for i in range(100):
            dep = self._create_dependency_from_dict(
                {
                    "name": f"test_dep_{i}",
                    "module": f"test.module.dep_{i}",
                    "type": "protocol",
                }
            )
            dependencies.append(dep)

        end_time = time.time()
        creation_time = end_time - start_time

        # Should create 100 dependencies in reasonable time (< 1 second)
        assert len(dependencies) == 100
        assert creation_time < 1.0  # Performance threshold

        # Test factory function performance with different input types
        start_time = time.time()

        for i in range(50):
            # String format
            self._create_dependency_from_string(f"ProtocolTest{i}")

            # Dict format
            self._create_dependency_from_dict(
                {"name": f"dict_dep_{i}", "type": "service"}
            )

        end_time = time.time()
        mixed_creation_time = end_time - start_time

        # Should handle mixed formats efficiently
        assert mixed_creation_time < 1.0
