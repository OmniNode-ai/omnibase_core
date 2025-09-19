"""
Test Four Node Archetype Models.

Based on ONEX four-node architecture: COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR patterns.
This validates that node models properly support the architectural patterns.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from omnibase_core.models.nodes import (
    ModelNodeType,
    ModelNodeCapability,
    ModelNodeInformation,
    ModelCliNodeExecutionInput,
    ModelMetadataNodeCollection,
)


class TestFourNodeArchetype:
    """Test the four node archetype patterns: COMPUTE, EFFECT, REDUCER, ORCHESTRATOR."""

    def test_compute_node_archetype(self):
        """Test COMPUTE node archetype characteristics."""
        # COMPUTE nodes: Pure functions, deterministic, stateless
        compute_nodes = [
            ModelNodeType.CONTRACT_TO_MODEL(),
            ModelNodeType.GENERATE_ERROR_CODES(),
            ModelNodeType.SCHEMA_TO_PYDANTIC(),
            ModelNodeType.TEMPLATE_ENGINE(),
        ]

        for node in compute_nodes:
            # COMPUTE nodes should be generators (produce output)
            assert node.is_generator, f"{node.name} should be a generator"

            # COMPUTE nodes typically don't require external dependencies
            assert node.execution_priority >= 0

            # Should have clear output types
            assert node.output_type is not None, f"{node.name} should have output_type"

            # Category should indicate computational work
            assert node.category in ['generation', 'template', 'schema'], f"Invalid category for {node.name}"

    def test_effect_node_archetype(self):
        """Test EFFECT node archetype characteristics."""
        # EFFECT nodes: Side effects, I/O operations, state changes
        effect_nodes = [
            ModelNodeType.FILE_GENERATOR(),
            ModelNodeType.NODE_GENERATOR(),
            ModelNodeType.LOGGER_EMIT_LOG_EVENT(),
        ]

        for node in effect_nodes:
            # EFFECT nodes should produce output/files
            assert node.is_generator, f"{node.name} should be a generator"

            # EFFECT nodes may have dependencies
            assert isinstance(node.dependencies, list)

            # Should have specific output types
            assert node.output_type in ['files', 'node', 'logs'], f"Invalid output_type for {node.name}"

    def test_reducer_node_archetype(self):
        """Test REDUCER node archetype characteristics."""
        # REDUCER nodes: Aggregate, validate, combine multiple inputs
        reducer_nodes = [
            ModelNodeType.VALIDATION_ENGINE(),
            ModelNodeType.PARITY_VALIDATOR_WITH_FIXES(),
            ModelNodeType.CONTRACT_COMPLIANCE(),
            ModelNodeType.SCHEMA_CONFORMANCE(),
        ]

        for node in reducer_nodes:
            # REDUCER nodes should be validators
            assert node.is_validator, f"{node.name} should be a validator"

            # Should have high execution priority for validation
            assert node.execution_priority >= 75, f"{node.name} should have high priority"

            # Should produce reports
            assert 'report' in node.output_type, f"{node.name} should produce reports"

            # Category should be validation
            assert node.category == 'validation', f"{node.name} should be validation category"

    def test_orchestrator_node_archetype(self):
        """Test ORCHESTRATOR node archetype characteristics."""
        # ORCHESTRATOR nodes: Coordinate, manage, route, control flow
        orchestrator_nodes = [
            ModelNodeType.NODE_MANAGER_RUNNER(),
            ModelNodeType.BACKEND_SELECTION(),
            ModelNodeType.NODE_DISCOVERY(),
            ModelNodeType.METADATA_LOADER(),
        ]

        for node in orchestrator_nodes:
            # ORCHESTRATOR nodes should have highest priority
            assert node.execution_priority >= 90, f"{node.name} should have highest priority"

            # Should have runtime or discovery categories
            assert node.category in ['runtime', 'discovery'], f"Invalid category for {node.name}"

            # Should coordinate other components
            assert node.output_type in ['result', 'backend', 'nodes', 'metadata'], f"Invalid output for {node.name}"

    def test_node_capability_archetype_mapping(self):
        """Test that capabilities map correctly to archetypes."""
        # COMPUTE capabilities
        compute_caps = [
            ModelNodeCapability.SUPPORTS_DRY_RUN(),
            ModelNodeCapability.SUPPORTS_SCHEMA_VALIDATION(),
        ]

        for cap in compute_caps:
            assert cap.performance_impact in ['low', 'medium'], f"COMPUTE should be low/medium impact"

        # EFFECT capabilities
        effect_caps = [
            ModelNodeCapability.SUPPORTS_BATCH_PROCESSING(),
            ModelNodeCapability.SUPPORTS_EVENT_BUS(),
        ]

        for cap in effect_caps:
            assert cap.configuration_required, f"EFFECT capabilities should require config"
            assert cap.performance_impact in ['medium', 'high'], f"EFFECT should be medium/high impact"

        # REDUCER capabilities
        reducer_caps = [
            ModelNodeCapability.SUPPORTS_ERROR_RECOVERY(),
            ModelNodeCapability.SUPPORTS_CORRELATION_ID(),
        ]

        for cap in reducer_caps:
            assert cap.performance_impact in ['low', 'medium'], f"REDUCER should be low/medium impact"

        # ORCHESTRATOR capabilities
        orchestrator_caps = [
            ModelNodeCapability.SUPPORTS_EVENT_DISCOVERY(),
            ModelNodeCapability.TELEMETRY_ENABLED(),
        ]

        for cap in orchestrator_caps:
            assert len(cap.dependencies) >= 0, f"ORCHESTRATOR may have dependencies"

    def test_node_information_archetype_patterns(self):
        """Test node information patterns for each archetype."""
        # Test COMPUTE node information
        compute_info = ModelNodeInformation(
            node_id="compute_001",
            node_name="CONTRACT_TO_MODEL",
            node_type="compute",
            node_version="1.0.0",
            capabilities=["supports_dry_run", "supports_schema_validation"],
            supported_operations=["generate", "validate", "transform"],
        )

        assert compute_info.node_type == "compute"
        assert "generate" in compute_info.supported_operations
        assert len(compute_info.capabilities) > 0

        # Test EFFECT node information
        effect_info = ModelNodeInformation(
            node_id="effect_001",
            node_name="FILE_GENERATOR",
            node_type="effect",
            node_version="1.0.0",
            capabilities=["supports_batch_processing"],
            supported_operations=["write", "create", "modify"],
        )

        assert effect_info.node_type == "effect"
        assert "write" in effect_info.supported_operations

        # Test REDUCER node information
        reducer_info = ModelNodeInformation(
            node_id="reducer_001",
            node_name="VALIDATION_ENGINE",
            node_type="reducer",
            node_version="1.0.0",
            capabilities=["supports_error_recovery"],
            supported_operations=["validate", "aggregate", "check"],
        )

        assert reducer_info.node_type == "reducer"
        assert "validate" in reducer_info.supported_operations

        # Test ORCHESTRATOR node information
        orchestrator_info = ModelNodeInformation(
            node_id="orchestrator_001",
            node_name="NODE_MANAGER_RUNNER",
            node_type="orchestrator",
            node_version="1.0.0",
            capabilities=["telemetry_enabled", "supports_event_discovery"],
            supported_operations=["manage", "coordinate", "route"],
        )

        assert orchestrator_info.node_type == "orchestrator"
        assert "coordinate" in orchestrator_info.supported_operations

    def test_cli_execution_archetype_support(self):
        """Test that CLI execution input supports all archetypes."""
        archetype_actions = {
            'compute': 'generate_models',
            'effect': 'create_files',
            'reducer': 'validate_contracts',
            'orchestrator': 'manage_nodes',
        }

        for archetype, action in archetype_actions.items():
            cli_input = ModelCliNodeExecutionInput(
                action=action,
                node_name=f"{archetype}_node",
                include_metadata=True,
                include_health_info=True,
                execution_context=f"{archetype}_context",
            )

            assert cli_input.action == action
            assert cli_input.node_name == f"{archetype}_node"
            assert cli_input.execution_context == f"{archetype}_context"

            # Test legacy dict conversion
            legacy_dict = cli_input.to_legacy_dict()
            assert legacy_dict['action'] == action
            assert legacy_dict['node_name'] == f"{archetype}_node"

    def test_metadata_collection_archetype_organization(self):
        """Test that metadata collection can organize nodes by archetype."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add nodes from each archetype
        archetype_nodes = {
            'compute_contract_model': {'name': 'CONTRACT_TO_MODEL', 'type': 'compute'},
            'effect_file_gen': {'name': 'FILE_GENERATOR', 'type': 'effect'},
            'reducer_validator': {'name': 'VALIDATION_ENGINE', 'type': 'reducer'},
            'orchestrator_manager': {'name': 'NODE_MANAGER_RUNNER', 'type': 'orchestrator'},
        }

        for node_name, node_data in archetype_nodes.items():
            success = collection.add_node(node_name, node_data)
            assert success, f"Failed to add {node_name}"

        # Verify organization
        assert collection.node_count == 4
        assert collection.health_score > 0

        # Test analytics by archetype
        analytics = collection.analytics
        assert analytics.total_nodes == 4

        # Should be able to get nodes by archetype
        for node_name in archetype_nodes:
            node = collection.get_node(node_name)
            assert node is not None

    def test_archetype_interaction_patterns(self):
        """Test how different archetypes interact with each other."""
        # ORCHESTRATOR -> COMPUTE -> EFFECT -> REDUCER pattern
        orchestrator = ModelNodeType.NODE_MANAGER_RUNNER()
        compute = ModelNodeType.CONTRACT_TO_MODEL()
        effect = ModelNodeType.FILE_GENERATOR()
        reducer = ModelNodeType.VALIDATION_ENGINE()

        # Check execution order by priority
        nodes_by_priority = [orchestrator, reducer, compute, effect]
        priorities = [node.execution_priority for node in nodes_by_priority]

        # Should be in descending order of priority
        assert priorities == sorted(priorities, reverse=True), "Execution priorities not ordered correctly"

        # Check dependency patterns
        assert effect.dependencies == ['TEMPLATE_ENGINE'], "EFFECT should depend on COMPUTE"

        # Check capability compatibility
        dry_run_cap = ModelNodeCapability.SUPPORTS_DRY_RUN()
        batch_cap = ModelNodeCapability.SUPPORTS_BATCH_PROCESSING()
        recovery_cap = ModelNodeCapability.SUPPORTS_ERROR_RECOVERY()

        # All archetypes should support dry run for testing
        assert not dry_run_cap.configuration_required
        assert dry_run_cap.performance_impact == 'low'

    def test_archetype_validation_rules(self):
        """Test validation rules specific to each archetype."""
        test_cases = [
            # (archetype, should_be_generator, should_be_validator, expected_category)
            ('compute', True, False, 'generation'),
            ('effect', True, False, 'template'),
            ('reducer', False, True, 'validation'),
            ('orchestrator', False, False, 'runtime'),
        ]

        archetype_factories = {
            'compute': ModelNodeType.CONTRACT_TO_MODEL,
            'effect': ModelNodeType.FILE_GENERATOR,
            'reducer': ModelNodeType.VALIDATION_ENGINE,
            'orchestrator': ModelNodeType.NODE_MANAGER_RUNNER,
        }

        for archetype, should_gen, should_val, expected_cat in test_cases:
            factory = archetype_factories[archetype]
            node = factory()

            assert node.is_generator == should_gen, f"{archetype} generator mismatch"
            assert node.is_validator == should_val, f"{archetype} validator mismatch"
            assert node.category == expected_cat, f"{archetype} category mismatch"

    def test_archetype_performance_characteristics(self):
        """Test performance characteristics expected for each archetype."""
        performance_expectations = {
            'compute': {'min_priority': 0, 'max_priority': 80, 'output_required': True},
            'effect': {'min_priority': 0, 'max_priority': 90, 'output_required': True},
            'reducer': {'min_priority': 75, 'max_priority': 100, 'output_required': True},
            'orchestrator': {'min_priority': 90, 'max_priority': 100, 'output_required': True},
        }

        archetype_nodes = {
            'compute': [ModelNodeType.CONTRACT_TO_MODEL(), ModelNodeType.TEMPLATE_ENGINE()],
            'effect': [ModelNodeType.FILE_GENERATOR(), ModelNodeType.NODE_GENERATOR()],
            'reducer': [ModelNodeType.VALIDATION_ENGINE(), ModelNodeType.CONTRACT_COMPLIANCE()],
            'orchestrator': [ModelNodeType.NODE_MANAGER_RUNNER(), ModelNodeType.NODE_DISCOVERY()],
        }

        for archetype, nodes in archetype_nodes.items():
            expectations = performance_expectations[archetype]

            for node in nodes:
                # Check priority range
                assert expectations['min_priority'] <= node.execution_priority <= expectations['max_priority'], \
                    f"{archetype} {node.name} priority {node.execution_priority} out of range"

                # Check output requirement
                if expectations['output_required']:
                    assert node.output_type is not None, f"{archetype} {node.name} should have output_type"

    @pytest.mark.parametrize("archetype,node_factory", [
        ('compute', ModelNodeType.CONTRACT_TO_MODEL),
        ('effect', ModelNodeType.FILE_GENERATOR),
        ('reducer', ModelNodeType.VALIDATION_ENGINE),
        ('orchestrator', ModelNodeType.NODE_MANAGER_RUNNER),
    ])
    def test_individual_archetype_compliance(self, archetype, node_factory):
        """Test individual archetype compliance."""
        node = node_factory()

        # All nodes should have basic properties
        assert node.name is not None
        assert node.description is not None
        assert node.category is not None

        # Test string representation
        assert str(node) == node.name

        # Test equality
        same_node = node_factory()
        assert node == same_node
        assert node == node.name

        # Test model validation
        node_dict = node.model_dump()
        restored_node = ModelNodeType.model_validate(node_dict)
        assert restored_node.name == node.name