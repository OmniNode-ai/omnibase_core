"""
Integration tests for node domain reorganization.

Tests that the reorganized node models work correctly together
and integrate properly with the rest of the system.
"""

import pytest
import uuid
from datetime import datetime
from typing import Dict, Any, List

from omnibase_core.models.nodes import (
    ModelCliNodeExecutionInput,
    ModelMetadataNodeCollection,
    ModelNodeCapability,
    ModelMetadataNodeInfo,
    ModelNodeType,
)


class TestNodeDomainIntegration:
    """Integration tests for node domain models."""

    def test_full_node_workflow_integration(self):
        """Test a complete workflow using all node models together."""
        # 1. Create node types for different archetypes
        compute_node = ModelNodeType.CONTRACT_TO_MODEL()
        effect_node = ModelNodeType.FILE_GENERATOR()
        reducer_node = ModelNodeType.VALIDATION_ENGINE()
        orchestrator_node = ModelNodeType.NODE_MANAGER_RUNNER()

        node_types = [compute_node, effect_node, reducer_node, orchestrator_node]

        # 2. Create capabilities for the nodes
        capabilities = [
            ModelNodeCapability.supports_dry_run(),
            ModelNodeCapability.supports_batch_processing(),
            ModelNodeCapability.supports_error_recovery(),
            ModelNodeCapability.telemetry_enabled(),
        ]

        # 3. Create node information for each type
        node_infos = []
        for i, (node_type, capability) in enumerate(zip(node_types, capabilities)):
            node_info = ModelMetadataNodeInfo(
                name=node_type.name,
                description=node_type.description,
                version="1.0.0",
                tags=[capability.value],
            )
            node_infos.append(node_info)

        # 4. Create metadata collection with all nodes
        collection = ModelMetadataNodeCollection.create_empty_collection()
        for node_info in node_infos:
            node_data = {
                "name": node_info.name,
                "description": node_info.description,
                "type": node_info.node_type,
            }
            success = collection.add_node(node_info.name, node_data, None)
            assert success, f"Failed to add {node_info.name}"

        # 5. Create CLI execution inputs for each node
        cli_inputs = []
        for node_info in node_infos:
            cli_input = ModelCliNodeExecutionInput(
                action="run_node",
                node_name=node_info.name,
                include_metadata=True,
                include_health_info=True,
                verbose=True,
                execution_context="integration_test",
                request_id=f"req_{node_info.name}",
            )
            cli_inputs.append(cli_input)

        # 6. Verify the complete integration
        assert collection.node_count == 4
        assert len(cli_inputs) == 4
        assert collection.health_score > 0

        # 7. Test cross-model interactions
        for cli_input in cli_inputs:
            node = collection.get_node(cli_input.node_name)
            assert node is not None

            node_info = collection.get_node_info(cli_input.node_name)
            assert node_info is not None
            assert node_info.name == cli_input.node_name

    def test_archetype_based_workflow(self):
        """Test workflow based on the four node archetypes."""
        # Define archetype workflow: ORCHESTRATOR -> COMPUTE -> EFFECT -> REDUCER
        workflow_nodes = [
            {
                "type": ModelNodeType.NODE_MANAGER_RUNNER(),
                "capability": ModelNodeCapability.telemetry_enabled(),
                "archetype": "orchestrator",
                "priority": 100,
            },
            {
                "type": ModelNodeType.CONTRACT_TO_MODEL(),
                "capability": ModelNodeCapability.supports_dry_run(),
                "archetype": "compute",
                "priority": 50,
            },
            {
                "type": ModelNodeType.FILE_GENERATOR(),
                "capability": ModelNodeCapability.supports_batch_processing(),
                "archetype": "effect",
                "priority": 40,
            },
            {
                "type": ModelNodeType.VALIDATION_ENGINE(),
                "capability": ModelNodeCapability.supports_error_recovery(),
                "archetype": "reducer",
                "priority": 80,
            },
        ]

        # Create workflow collection
        workflow_collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add nodes in archetype order
        for i, workflow_node in enumerate(workflow_nodes):
            node_type = workflow_node["type"]
            capability = workflow_node["capability"]
            archetype = workflow_node["archetype"]

            # Create node information
            node_info = ModelMetadataNodeInfo(
                name=node_type.name,
                description=f"{archetype.title()} archetype: {node_type.description}",
                version="2.0.0",
                tags=[capability.value],
                dependencies=self._get_archetype_dependencies(archetype),
            )

            # Create node data
            node_data = {
                "name": node_type.name,
                "description": node_type.description,
                "archetype": archetype,
                "priority": workflow_node["priority"],
            }

            # Add to collection
            success = workflow_collection.add_node(node_type.name, node_data, node_info)
            assert success

        # Verify workflow integrity
        assert workflow_collection.node_count == 4

        # Test execution order by priority
        node_priorities = []
        for node_name in ["NODE_MANAGER_RUNNER", "CONTRACT_TO_MODEL", "FILE_GENERATOR", "VALIDATION_ENGINE"]:
            node_info = workflow_collection.get_node_info(node_name)
            assert node_info is not None
            node_priorities.append((node_name, workflow_nodes[["NODE_MANAGER_RUNNER", "CONTRACT_TO_MODEL", "FILE_GENERATOR", "VALIDATION_ENGINE"].index(node_name)]["priority"]))

        # Sort by priority (highest first)
        sorted_priorities = sorted(node_priorities, key=lambda x: x[1], reverse=True)
        expected_order = ["NODE_MANAGER_RUNNER", "VALIDATION_ENGINE", "CONTRACT_TO_MODEL", "FILE_GENERATOR"]
        actual_order = [name for name, _ in sorted_priorities]
        assert actual_order == expected_order

    def test_cli_execution_with_collection_lookup(self):
        """Test CLI execution that looks up nodes in a collection."""
        # Create a collection with various node types
        collection = ModelMetadataNodeCollection.create_empty_collection()

        nodes_to_add = [
            ("CONTRACT_TO_MODEL", "generation", ["supports_dry_run"]),
            ("VALIDATION_ENGINE", "validation", ["supports_error_recovery"]),
            ("FILE_GENERATOR", "template", ["supports_batch_processing"]),
            ("NODE_DISCOVERY", "discovery", ["supports_correlation_id"]),
        ]

        for node_name, category, capabilities in nodes_to_add:
            node_type = ModelNodeType.from_string(node_name)
            node_info = ModelMetadataNodeInfo(
                name=node_name,
                description=f"Node for {category}",
                version="1.0.0",
                tags=capabilities,
            )

            node_data = {"name": node_name, "category": category}
            collection.add_node(node_name, node_data, node_info)

        # Create CLI inputs for different operations
        cli_operations = [
            ("list_nodes", None, True),
            ("node_info", "CONTRACT_TO_MODEL", True),
            ("run_node", "VALIDATION_ENGINE", False),
            ("discover_nodes", "NODE_DISCOVERY", True),
        ]

        for action, target_node, include_metadata in cli_operations:
            cli_input = ModelCliNodeExecutionInput(
                action=action,
                node_name=target_node,
                include_metadata=include_metadata,
                category_filter="generation" if action == "list_nodes" else None,
                timeout_seconds=30.0,
                execution_context="cli_integration_test",
            )

            # Verify CLI input can find corresponding node
            if target_node:
                node = collection.get_node(target_node)
                assert node is not None, f"Node {target_node} not found for action {action}"

                node_info = collection.get_node_info(target_node)
                assert node_info is not None
                assert node_info.name == target_node

            # Test legacy dict conversion
            legacy_dict = cli_input.to_legacy_dict()
            assert legacy_dict["action"] == action

            # Test roundtrip
            restored_cli = ModelCliNodeExecutionInput.from_legacy_dict(legacy_dict)
            assert restored_cli.action == cli_input.action

    def test_capability_dependency_resolution(self):
        """Test capability dependency resolution across models."""
        # Create capabilities with dependencies
        base_capability = ModelNodeCapability.supports_schema_validation()
        dependent_capability = ModelNodeCapability.supports_custom_handlers()
        complex_capability = ModelNodeCapability.supports_event_discovery()

        # Verify dependency chain
        assert "SUPPORTS_SCHEMA_VALIDATION" in dependent_capability.dependencies
        assert "SUPPORTS_EVENT_BUS" in complex_capability.dependencies
        assert "SUPPORTS_SCHEMA_VALIDATION" in complex_capability.dependencies

        # Create nodes with capability dependencies
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Base node with fundamental capability
        base_node_info = ModelMetadataNodeInfo(
            name="SCHEMA_VALIDATOR",
            description="Schema validation node",
            version="1.0.0",
            tags=[base_capability.value],
        )

        # Dependent node
        dependent_node_info = ModelMetadataNodeInfo(
            name="CUSTOM_HANDLER",
            description="Custom handler node",
            version="1.0.0",
            tags=[dependent_capability.value],
            dependencies=["SCHEMA_VALIDATOR"],
        )

        # Complex node with multiple dependencies
        complex_node_info = ModelMetadataNodeInfo(
            name="EVENT_DISCOVERER",
            description="Event discovery node",
            version="1.0.0",
            tags=[complex_capability.value],
            dependencies=["SCHEMA_VALIDATOR", "EVENT_BUS"],
        )

        # Add to collection
        for node_info in [base_node_info, dependent_node_info, complex_node_info]:
            node_data = {"name": node_info.name, "type": "default"}
            success = collection.add_node(node_info.name, node_data, node_info)
            assert success

        # Verify dependency resolution
        complex_node = collection.get_node_info("EVENT_DISCOVERER")
        assert "SCHEMA_VALIDATOR" in complex_node.dependencies

        dependent_node = collection.get_node_info("CUSTOM_HANDLER")
        assert "SCHEMA_VALIDATOR" in dependent_node.dependencies

    def test_node_type_and_capability_compatibility(self):
        """Test compatibility between node types and capabilities."""
        compatibility_matrix = [
            # (node_type, capability, should_be_compatible)
            (ModelNodeType.CONTRACT_TO_MODEL(), ModelNodeCapability.supports_dry_run(), True),
            (ModelNodeType.FILE_GENERATOR(), ModelNodeCapability.supports_batch_processing(), True),
            (ModelNodeType.VALIDATION_ENGINE(), ModelNodeCapability.supports_error_recovery(), True),
            (ModelNodeType.NODE_MANAGER_RUNNER(), ModelNodeCapability.telemetry_enabled(), True),
        ]

        for node_type, capability, should_be_compatible in compatibility_matrix:
            # Create node information combining type and capability
            node_info = ModelMetadataNodeInfo(
                name=node_type.name,
                description=f"{node_type.description} with {capability.description}",
                version="1.0.0",
                tags=[capability.value],
            )

            # Verify compatibility
            if should_be_compatible:
                assert capability.value in node_info.tags

            # Test CLI execution for this combination
            cli_input = ModelCliNodeExecutionInput(
                action="run_node",
                node_name=node_type.name,
                include_metadata=True,
                execution_context="compatibility_test",
            )

            assert cli_input.node_name == node_type.name

    def test_metadata_collection_analytics_integration(self):
        """Test integration between metadata collection and analytics."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add nodes of different archetypes
        archetype_data = [
            ("COMPUTE_NODE_1", "compute", "active", "healthy"),
            ("COMPUTE_NODE_2", "compute", "active", "healthy"),
            ("EFFECT_NODE_1", "effect", "active", "degraded"),
            ("REDUCER_NODE_1", "reducer", "maintenance", "healthy"),
            ("ORCHESTRATOR_NODE_1", "orchestrator", "active", "healthy"),
        ]

        for node_name, archetype, status, health in archetype_data:
            node_info = ModelMetadataNodeInfo(
                name=node_name,
                description=f"{archetype} node",
                version="1.0.0",
            )

            node_data = {"name": node_name, "archetype": archetype}
            collection.add_node(node_name, node_data, node_info)

        # Verify analytics
        analytics = collection.analytics
        assert analytics.total_nodes == 5

        # Check collection health
        health_score = collection.health_score
        assert 0 <= health_score <= 100

        # Test CLI operations on the collection
        cli_operations = [
            ModelCliNodeExecutionInput(
                action="list_nodes",
                category_filter="compute",
                health_filter=True,
            ),
            ModelCliNodeExecutionInput(
                action="health_check",
                include_health_info=True,
            ),
            ModelCliNodeExecutionInput(
                action="node_info",
                target_node="ORCHESTRATOR_NODE_1",
                include_metadata=True,
            ),
        ]

        for cli_input in cli_operations:
            # Should be able to serialize/deserialize
            serialized = cli_input.model_dump()
            restored = ModelCliNodeExecutionInput.model_validate(serialized)
            assert restored.action == cli_input.action

    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases in integration."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Test adding invalid nodes
        invalid_node_attempts = [
            ("123invalid", {"name": "invalid"}),  # Invalid name
            ("valid_name", None),                  # None data
        ]

        for node_name, node_data in invalid_node_attempts:
            success = collection.add_node(node_name, node_data)
            assert not success  # Should fail gracefully

        # Test CLI with non-existent nodes
        cli_input = ModelCliNodeExecutionInput(
            action="node_info",
            target_node="NON_EXISTENT_NODE",
        )

        # Should create valid CLI input even if node doesn't exist
        assert cli_input.target_node == "NON_EXISTENT_NODE"

        # Test capability with invalid versions
        capability = ModelNodeCapability.telemetry_enabled()
        assert not capability.is_compatible_with_version("0.9.0")  # Too old
        assert capability.is_compatible_with_version("1.1.0")     # Compatible

    def test_serialization_integration(self):
        """Test serialization integration across all models."""
        # Create instances of all models
        node_type = ModelNodeType.CONTRACT_TO_MODEL()
        capability = ModelNodeCapability.supports_dry_run()
        node_info = ModelMetadataNodeInfo(
            name="SERIAL_NODE",
            description="Serialization test node",
            version="1.0.0",
            tags=[capability.value],
        )
        cli_input = ModelCliNodeExecutionInput(
            action="test_serialization",
            node_name="SERIAL_NODE",
        )

        collection = ModelMetadataNodeCollection.create_empty_collection()
        collection.add_node("SERIAL_NODE", {"name": "SERIAL_NODE"}, node_info)

        # Test individual serialization
        models_to_test = [
            ("node_type", node_type),
            ("capability", capability),
            ("node_info", node_info),
            ("cli_input", cli_input),
            ("collection", collection),
        ]

        serialized_data = {}
        for name, model in models_to_test:
            serialized = model.model_dump()
            assert isinstance(serialized, dict)
            serialized_data[name] = serialized

        # Test deserialization
        for name, original_model in models_to_test:
            model_class = type(original_model)
            restored = model_class.model_validate(serialized_data[name])

            # Basic equality checks
            if hasattr(original_model, 'name'):
                assert restored.name == original_model.name
            if hasattr(original_model, 'action'):
                assert restored.action == original_model.action
            if hasattr(original_model, 'node_id'):
                assert restored.node_id == original_model.node_id

    def _get_archetype_operations(self, archetype: str) -> List[str]:
        """Get typical operations for an archetype."""
        operations_map = {
            "compute": ["generate", "transform", "calculate"],
            "effect": ["create", "write", "modify", "delete"],
            "reducer": ["validate", "aggregate", "check", "verify"],
            "orchestrator": ["manage", "coordinate", "route", "schedule"],
        }
        return operations_map.get(archetype, ["execute"])

    def _get_archetype_dependencies(self, archetype: str) -> List[str]:
        """Get typical dependencies for an archetype."""
        dependencies_map = {
            "compute": [],
            "effect": ["COMPUTE_ENGINE"],
            "reducer": ["DATA_SOURCE"],
            "orchestrator": ["ALL_NODES"],
        }
        return dependencies_map.get(archetype, [])