# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Integration tests for ModelHandlerDescriptor: YAML contract to handler instantiation flow.

These tests verify the complete workflow from YAML contract to runtime handler:
1. Define/load a YAML contract (or inline YAML data)
2. Parse it into a ModelHandlerDescriptor
3. Use the descriptor to instantiate a handler
4. Verify the handler works correctly

This demonstrates the full end-to-end flow as documented in the handlers module.
"""

import importlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_handler_capability import EnumHandlerCapability
from omnibase_core.enums.enum_handler_command_type import EnumHandlerCommandType
from omnibase_core.enums.enum_handler_role import EnumHandlerRole
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.models.handlers import ModelHandlerDescriptor, ModelIdentifier
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Test configuration
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60


# =============================================================================
# Mock Handler Classes for Testing
# =============================================================================


class MockHandler(ABC):
    """Abstract base class for mock handlers used in integration tests."""

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """Execute the handler's main operation."""
        ...

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """Validate input data."""
        ...


class MockValidatorHandler(MockHandler):
    """Mock validator handler for testing compute handler instantiation.

    This simulates a real COMPUTE_HANDLER that performs validation.
    """

    def __init__(self) -> None:
        """Initialize the mock validator handler."""
        self._validations_performed = 0

    def execute(self, data: Any) -> dict[str, Any]:
        """Execute validation and return result."""
        is_valid = self.validate(data)
        return {
            "valid": is_valid,
            "data": data,
            "validations_performed": self._validations_performed,
        }

    def validate(self, data: Any) -> bool:
        """Validate the input data is not empty."""
        self._validations_performed += 1
        if data is None:
            return False
        if isinstance(data, str) and len(data) == 0:
            return False
        if isinstance(data, dict) and len(data) == 0:
            return False
        return True


class MockKafkaAdapter(MockHandler):
    """Mock Kafka adapter for testing adapter instantiation.

    This simulates a KAFKA adapter that performs I/O operations.
    """

    def __init__(self) -> None:
        """Initialize the mock Kafka adapter."""
        self._messages_processed = 0

    def execute(self, data: Any) -> dict[str, Any]:
        """Process a message (simulated)."""
        self._messages_processed += 1
        return {
            "status": "processed",
            "data": data,
            "message_count": self._messages_processed,
        }

    def validate(self, data: Any) -> bool:
        """Validate message format."""
        return data is not None


# =============================================================================
# YAML Contract Parsing Utilities
# =============================================================================


def parse_yaml_to_descriptor(contract_data: dict[str, Any]) -> ModelHandlerDescriptor:
    """Parse YAML contract data into a ModelHandlerDescriptor.

    This function demonstrates the contract-to-descriptor transformation
    that occurs at runtime when loading handler contracts.

    Args:
        contract_data: Dictionary loaded from YAML contract file.

    Returns:
        ModelHandlerDescriptor ready for use in handler instantiation.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    # Parse handler_name from string format "namespace:name[@variant]"
    handler_name_str = contract_data["handler_name"]
    handler_name = ModelIdentifier.parse(handler_name_str)

    # Parse semantic version
    version_str = contract_data["handler_version"]
    version_parts = version_str.split(".")
    handler_version = ModelSemVer(
        major=int(version_parts[0]),
        minor=int(version_parts[1]),
        patch=int(version_parts[2]),
    )

    # Parse enum values
    handler_role = EnumHandlerRole[contract_data["handler_role"]]
    handler_type = EnumHandlerType[contract_data["handler_type"]]
    handler_type_category = EnumHandlerTypeCategory[
        contract_data["handler_type_category"]
    ]

    # Parse capabilities (optional)
    capabilities = [
        EnumHandlerCapability[cap] for cap in contract_data.get("capabilities", [])
    ]

    # Parse commands_accepted (optional)
    commands_accepted = [
        EnumHandlerCommandType[cmd]
        for cmd in contract_data.get("commands_accepted", [])
    ]

    return ModelHandlerDescriptor(
        handler_name=handler_name,
        handler_version=handler_version,
        handler_role=handler_role,
        handler_type=handler_type,
        handler_type_category=handler_type_category,
        is_adapter=contract_data.get("is_adapter", False),
        capabilities=capabilities,
        commands_accepted=commands_accepted,
        import_path=contract_data.get("import_path"),
    )


def instantiate_handler_from_descriptor(
    descriptor: ModelHandlerDescriptor,
    handler_registry: dict[str, type[MockHandler]] | None = None,
) -> MockHandler:
    """Instantiate a handler from its descriptor.

    This demonstrates the descriptor-to-handler instantiation pattern.

    Args:
        descriptor: The handler descriptor containing instantiation info.
        handler_registry: Optional registry mapping import paths to handler classes
            (used for testing without actual module imports).

    Returns:
        Instantiated handler ready for use.

    Raises:
        ValueError: If descriptor has no instantiation method.
        ImportError: If import_path module cannot be found.
        AttributeError: If class not found in module.
    """
    if not descriptor.has_instantiation_method:
        raise ValueError(
            f"Descriptor {descriptor.handler_name} has no instantiation method"
        )

    if descriptor.import_path:
        # In production, we would use importlib
        # For testing, we use a registry to avoid actual module imports
        if handler_registry and descriptor.import_path in handler_registry:
            handler_class = handler_registry[descriptor.import_path]
            return handler_class()

        # Fallback to actual import (for real handlers)
        module_path, class_name = descriptor.import_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        handler_class = getattr(module, class_name)
        return handler_class()

    raise ValueError(
        f"Artifact-based instantiation not supported in this test: {descriptor}"
    )


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestYamlContractToDescriptor:
    """Tests for YAML contract parsing into ModelHandlerDescriptor."""

    def test_parse_compute_handler_contract(self) -> None:
        """Test parsing a COMPUTE_HANDLER YAML contract into descriptor."""
        # Arrange: Define YAML contract data (simulating loaded YAML)
        contract_data = {
            "handler_name": "onex:schema-validator",
            "handler_version": "1.0.0",
            "handler_role": "COMPUTE_HANDLER",
            "handler_type": "NAMED",
            "handler_type_category": "COMPUTE",
            "capabilities": ["VALIDATE", "CACHE", "IDEMPOTENT"],
            "commands_accepted": ["EXECUTE", "VALIDATE"],
            "import_path": "tests.integration.models.handlers.test_handler_descriptor_integration.MockValidatorHandler",
        }

        # Act: Parse into descriptor
        descriptor = parse_yaml_to_descriptor(contract_data)

        # Assert: Verify descriptor properties
        assert descriptor.handler_name.namespace == "onex"
        assert descriptor.handler_name.name == "schema-validator"
        assert descriptor.handler_version.major == 1
        assert descriptor.handler_version.minor == 0
        assert descriptor.handler_version.patch == 0
        assert descriptor.handler_role == EnumHandlerRole.COMPUTE_HANDLER
        assert descriptor.handler_type == EnumHandlerType.NAMED
        assert descriptor.handler_type_category == EnumHandlerTypeCategory.COMPUTE
        assert descriptor.is_adapter is False
        assert EnumHandlerCapability.VALIDATE in descriptor.capabilities
        assert EnumHandlerCapability.CACHE in descriptor.capabilities
        assert EnumHandlerCapability.IDEMPOTENT in descriptor.capabilities
        assert EnumHandlerCommandType.EXECUTE in descriptor.commands_accepted
        assert descriptor.has_instantiation_method is True

    def test_parse_adapter_contract(self) -> None:
        """Test parsing an adapter YAML contract into descriptor."""
        # Arrange: Define Kafka adapter contract
        contract_data = {
            "handler_name": "onex:kafka-ingress@v2",
            "handler_version": "2.1.0",
            "handler_role": "INFRA_HANDLER",
            "handler_type": "KAFKA",
            "handler_type_category": "EFFECT",
            "is_adapter": True,
            "capabilities": ["STREAM", "ASYNC", "BATCH"],
            "commands_accepted": ["EXECUTE", "HEALTH_CHECK"],
            "import_path": "omnibase_infra.adapters.kafka.KafkaIngressAdapter",
        }

        # Act
        descriptor = parse_yaml_to_descriptor(contract_data)

        # Assert
        assert descriptor.handler_name.namespace == "onex"
        assert descriptor.handler_name.name == "kafka-ingress"
        assert descriptor.handler_name.variant == "v2"
        assert descriptor.handler_version.major == 2
        assert descriptor.handler_version.minor == 1
        assert descriptor.is_adapter is True
        assert descriptor.handler_type == EnumHandlerType.KAFKA
        assert descriptor.handler_type_category == EnumHandlerTypeCategory.EFFECT
        assert EnumHandlerCapability.STREAM in descriptor.capabilities

    def test_parse_minimal_contract(self) -> None:
        """Test parsing a minimal YAML contract with only required fields."""
        contract_data = {
            "handler_name": "vendor:simple-handler",
            "handler_version": "0.1.0",
            "handler_role": "NODE_HANDLER",
            "handler_type": "HTTP",
            "handler_type_category": "EFFECT",
        }

        descriptor = parse_yaml_to_descriptor(contract_data)

        assert descriptor.handler_name.namespace == "vendor"
        assert descriptor.handler_name.name == "simple-handler"
        assert descriptor.handler_name.variant is None
        assert descriptor.is_adapter is False
        assert descriptor.capabilities == []
        assert descriptor.commands_accepted == []
        assert descriptor.import_path is None
        assert descriptor.has_instantiation_method is False

    def test_load_yaml_from_file(self, tmp_path: Path) -> None:
        """Test loading YAML contract from actual file."""
        # Arrange: Create temporary YAML file
        yaml_content = """
handler_name: "onex:file-validator"
handler_version: "1.2.3"
handler_role: COMPUTE_HANDLER
handler_type: NAMED
handler_type_category: COMPUTE
capabilities:
  - VALIDATE
  - CACHE
commands_accepted:
  - EXECUTE
import_path: "mypackage.handlers.FileValidator"
"""
        temp_file = tmp_path / "test_contract.yaml"
        temp_file.write_text(yaml_content, encoding="utf-8")

        # Act: Load and parse
        with open(temp_file) as f:
            contract_data = yaml.safe_load(f)

        descriptor = parse_yaml_to_descriptor(contract_data)

        # Assert
        assert descriptor.handler_name.namespace == "onex"
        assert descriptor.handler_name.name == "file-validator"
        assert descriptor.handler_version.major == 1
        assert descriptor.handler_version.minor == 2
        assert descriptor.handler_version.patch == 3
        assert descriptor.has_instantiation_method is True


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestDescriptorToHandlerInstantiation:
    """Tests for handler instantiation from descriptor."""

    def test_instantiate_compute_handler(self) -> None:
        """Test instantiating a compute handler from descriptor."""
        # Arrange: Create descriptor with mock handler import path
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="validator"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            capabilities=[EnumHandlerCapability.VALIDATE],
            import_path="mock.validator.Handler",
        )

        # Create mock registry
        handler_registry = {
            "mock.validator.Handler": MockValidatorHandler,
        }

        # Act: Instantiate handler
        handler = instantiate_handler_from_descriptor(descriptor, handler_registry)

        # Assert: Handler is correct type and works
        assert isinstance(handler, MockValidatorHandler)
        result = handler.execute({"key": "value"})
        assert result["valid"] is True
        assert result["validations_performed"] == 1

    def test_instantiate_adapter_handler(self) -> None:
        """Test instantiating an adapter handler from descriptor."""
        # Arrange
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="kafka-adapter"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.KAFKA,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=True,
            capabilities=[EnumHandlerCapability.STREAM, EnumHandlerCapability.ASYNC],
            import_path="mock.kafka.Adapter",
        )

        handler_registry = {
            "mock.kafka.Adapter": MockKafkaAdapter,
        }

        # Act
        handler = instantiate_handler_from_descriptor(descriptor, handler_registry)

        # Assert
        assert isinstance(handler, MockKafkaAdapter)
        result = handler.execute({"topic": "test", "payload": "data"})
        assert result["status"] == "processed"
        assert result["message_count"] == 1

    def test_metadata_only_descriptor_raises_error(self) -> None:
        """Test that metadata-only descriptor raises error on instantiation."""
        # Arrange: Descriptor without import_path or artifact_ref
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="metadata-only"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            instantiate_handler_from_descriptor(descriptor)

        assert "no instantiation method" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestEndToEndYamlToHandlerFlow:
    """End-to-end tests for complete YAML to handler flow."""

    def test_yaml_contract_to_working_handler(self) -> None:
        """Test complete flow: YAML contract -> descriptor -> handler -> execution."""
        # Step 1: Define YAML contract (simulating file load)
        yaml_content = """
handler_name: "onex:integration-validator"
handler_version: "1.0.0"
handler_role: COMPUTE_HANDLER
handler_type: NAMED
handler_type_category: COMPUTE
capabilities:
  - VALIDATE
  - CACHE
  - IDEMPOTENT
commands_accepted:
  - EXECUTE
  - VALIDATE
import_path: "mock.integration.Validator"
"""
        contract_data = yaml.safe_load(yaml_content)

        # Step 2: Parse into descriptor
        descriptor = parse_yaml_to_descriptor(contract_data)

        # Verify descriptor
        assert descriptor.handler_name.namespace == "onex"
        assert descriptor.handler_name.name == "integration-validator"
        assert descriptor.has_instantiation_method is True

        # Step 3: Instantiate handler using registry
        handler_registry = {
            "mock.integration.Validator": MockValidatorHandler,
        }
        handler = instantiate_handler_from_descriptor(descriptor, handler_registry)

        # Step 4: Use handler and verify it works
        assert isinstance(handler, MockValidatorHandler)

        # Test valid data
        result = handler.execute({"user": "test_user", "action": "login"})
        assert result["valid"] is True

        # Test invalid data (empty dict)
        result = handler.execute({})
        assert result["valid"] is False

        # Verify tracking
        assert result["validations_performed"] == 2

    def test_capability_based_routing_with_descriptors(self) -> None:
        """Test using descriptors for capability-based handler selection."""
        # Create a registry of handlers with different capabilities
        descriptors = [
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="fast-validator"),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.COMPUTE_HANDLER,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
                capabilities=[
                    EnumHandlerCapability.CACHE,
                    EnumHandlerCapability.IDEMPOTENT,
                ],
                import_path="mock.fast.Validator",
            ),
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="strict-validator"),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.COMPUTE_HANDLER,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
                capabilities=[EnumHandlerCapability.VALIDATE],
                import_path="mock.strict.Validator",
            ),
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="full-validator"),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.COMPUTE_HANDLER,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
                capabilities=[
                    EnumHandlerCapability.VALIDATE,
                    EnumHandlerCapability.CACHE,
                    EnumHandlerCapability.IDEMPOTENT,
                ],
                import_path="mock.full.Validator",
            ),
        ]

        # Find handlers with ALL required capabilities
        required_caps = {EnumHandlerCapability.CACHE, EnumHandlerCapability.IDEMPOTENT}
        matching = [
            d for d in descriptors if required_caps.issubset(set(d.capabilities))
        ]

        # Should match fast-validator and full-validator
        assert len(matching) == 2
        handler_names = {d.handler_name.name for d in matching}
        assert "fast-validator" in handler_names
        assert "full-validator" in handler_names
        assert "strict-validator" not in handler_names

    def test_version_specific_handler_selection(self) -> None:
        """Test selecting handlers based on version requirements."""
        # Create descriptors with different versions
        descriptors = [
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="api-handler"),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.INFRA_HANDLER,
                handler_type=EnumHandlerType.HTTP,
                handler_type_category=EnumHandlerTypeCategory.EFFECT,
                import_path="v1.handler",
            ),
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="api-handler"),
                handler_version=ModelSemVer(major=2, minor=0, patch=0),
                handler_role=EnumHandlerRole.INFRA_HANDLER,
                handler_type=EnumHandlerType.HTTP,
                handler_type_category=EnumHandlerTypeCategory.EFFECT,
                import_path="v2.handler",
            ),
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="api-handler"),
                handler_version=ModelSemVer(major=2, minor=1, patch=0),
                handler_role=EnumHandlerRole.INFRA_HANDLER,
                handler_type=EnumHandlerType.HTTP,
                handler_type_category=EnumHandlerTypeCategory.EFFECT,
                import_path="v2.1.handler",
            ),
        ]

        # Find handlers with major version 2
        v2_handlers = [d for d in descriptors if d.handler_version.major == 2]

        assert len(v2_handlers) == 2

        # Find latest v2
        latest_v2 = max(
            v2_handlers,
            key=lambda d: (
                d.handler_version.major,
                d.handler_version.minor,
                d.handler_version.patch,
            ),
        )
        assert latest_v2.handler_version.minor == 1
        assert latest_v2.import_path == "v2.1.handler"


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestDescriptorSerializationRoundtrip:
    """Tests for descriptor serialization and roundtrip consistency."""

    def test_yaml_to_descriptor_to_dict_roundtrip(self) -> None:
        """Test that YAML -> descriptor -> dict -> descriptor is consistent."""
        # Original YAML data
        original_yaml = {
            "handler_name": "onex:roundtrip-test",
            "handler_version": "1.2.3",
            "handler_role": "COMPUTE_HANDLER",
            "handler_type": "NAMED",
            "handler_type_category": "COMPUTE",
            "capabilities": ["VALIDATE", "CACHE"],
            "commands_accepted": ["EXECUTE"],
            "import_path": "test.handler.Roundtrip",
        }

        # Parse to descriptor
        descriptor1 = parse_yaml_to_descriptor(original_yaml)

        # Serialize to dict
        serialized = descriptor1.model_dump()

        # Create new descriptor from serialized dict
        descriptor2 = ModelHandlerDescriptor(**serialized)

        # Verify consistency
        assert descriptor1.handler_name == descriptor2.handler_name
        assert descriptor1.handler_version == descriptor2.handler_version
        assert descriptor1.handler_role == descriptor2.handler_role
        assert descriptor1.handler_type == descriptor2.handler_type
        assert descriptor1.handler_type_category == descriptor2.handler_type_category
        assert descriptor1.capabilities == descriptor2.capabilities
        assert descriptor1.import_path == descriptor2.import_path

    def test_json_serialization_for_transport(self) -> None:
        """Test JSON serialization for network transport or storage."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="json-test"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            capabilities=[EnumHandlerCapability.CACHE],
            import_path="test.json.Handler",
        )

        # Serialize to JSON
        json_str = descriptor.model_dump_json()

        # Parse back
        import json

        data = json.loads(json_str)

        # Create new descriptor
        restored = ModelHandlerDescriptor(**data)

        assert restored.handler_name.namespace == "onex"
        assert restored.handler_name.name == "json-test"
        assert restored.import_path == "test.json.Handler"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
