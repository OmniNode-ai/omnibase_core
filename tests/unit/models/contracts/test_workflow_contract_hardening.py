# SPDX-FileCopyrightText: 2024 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for workflow contract model hardening (OMN-654).

Tests verify frozen=True and extra="forbid" behavior per OMN-490 patterns.

These tests ensure:
- Models are immutable after creation (frozen=True)
- Extra fields are rejected at instantiation (extra="forbid")
- Valid instantiation works with required fields
- Field constraints are properly enforced
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
)
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_node import (
    ModelWorkflowNode,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelWorkflowDefinitionHardening:
    """Tests for ModelWorkflowDefinition frozen and extra=forbid behavior."""

    def test_valid_instantiation(self) -> None:
        """Verify ModelWorkflowDefinition can be created with valid data."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )
        coordination_rules = ModelCoordinationRules(
            version=DEFAULT_VERSION,
        )

        definition = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
            coordination_rules=coordination_rules,
        )

        assert definition.version == DEFAULT_VERSION
        assert definition.workflow_metadata.workflow_name == "test-workflow"
        assert definition.execution_graph.nodes == []
        assert (
            definition.coordination_rules.failure_recovery_strategy
            == EnumFailureRecoveryStrategy.RETRY
        )

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowDefinition is immutable after creation."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )

        definition = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
        )

        with pytest.raises(ValidationError):
            definition.version = ModelSemVer(major=2, minor=0, patch=0)  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Verify extra fields are rejected."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowDefinition(
                version=DEFAULT_VERSION,
                workflow_metadata=metadata,
                execution_graph=execution_graph,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowDefinition.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowDefinition.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )

        original = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
        )

        new_version = ModelSemVer(major=2, minor=0, patch=0)
        modified = original.model_copy(update={"version": new_version})

        assert original.version == DEFAULT_VERSION  # Original unchanged
        assert modified.version == new_version  # Copy has new value


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelWorkflowDefinitionMetadataHardening:
    """Tests for ModelWorkflowDefinitionMetadata frozen and extra=forbid behavior."""

    def test_valid_instantiation(self) -> None:
        """Verify ModelWorkflowDefinitionMetadata can be created with valid data."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
        )

        assert metadata.version == DEFAULT_VERSION
        assert metadata.workflow_name == "test-workflow"
        assert metadata.workflow_version == DEFAULT_VERSION
        assert metadata.description == "A test workflow"
        assert metadata.execution_mode == "sequential"  # Default
        assert metadata.timeout_ms == 600000  # Default

    def test_valid_instantiation_with_custom_values(self) -> None:
        """Verify ModelWorkflowDefinitionMetadata accepts custom values."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="parallel-workflow",
            workflow_version=ModelSemVer(major=2, minor=1, patch=0),
            description="A parallel workflow",
            execution_mode="parallel",
            timeout_ms=300000,
        )

        assert metadata.execution_mode == "parallel"
        assert metadata.timeout_ms == 300000

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowDefinitionMetadata is immutable after creation."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
        )

        with pytest.raises(ValidationError):
            metadata.workflow_name = "new-name"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowDefinitionMetadata(
                version=DEFAULT_VERSION,
                workflow_name="test-workflow",
                workflow_version=DEFAULT_VERSION,
                description="A test workflow",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_timeout_ms_bounds(self) -> None:
        """Verify timeout_ms constraint (ge=1000)."""
        # Valid timeout
        valid = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
            timeout_ms=1000,
        )
        assert valid.timeout_ms == 1000

        # Too small (must be >= 1000)
        with pytest.raises(ValidationError):
            ModelWorkflowDefinitionMetadata(
                version=DEFAULT_VERSION,
                workflow_name="test-workflow",
                workflow_version=DEFAULT_VERSION,
                description="A test workflow",
                timeout_ms=999,
            )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowDefinitionMetadata.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowDefinitionMetadata.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test-workflow",
            workflow_version=DEFAULT_VERSION,
            description="A test workflow",
            timeout_ms=60000,
        )

        modified = original.model_copy(update={"timeout_ms": 120000})

        assert original.timeout_ms == 60000  # Original unchanged
        assert modified.timeout_ms == 120000  # Copy has new value


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelWorkflowStepHardening:
    """Tests for ModelWorkflowStep frozen and extra=forbid behavior."""

    def test_valid_instantiation(self) -> None:
        """Verify ModelWorkflowStep can be created with valid data."""
        step = ModelWorkflowStep(
            step_name="process-data",
            step_type="compute",
        )

        assert step.step_name == "process-data"
        assert step.step_type == "compute"
        assert step.timeout_ms == 30000  # Default
        assert step.retry_count == 3  # Default
        assert step.enabled is True  # Default
        assert step.priority == 100  # Default

    def test_valid_instantiation_with_custom_values(self) -> None:
        """Verify ModelWorkflowStep accepts custom values."""
        step_id = uuid4()
        correlation_id = uuid4()
        depends_on = [uuid4(), uuid4()]

        step = ModelWorkflowStep(
            correlation_id=correlation_id,
            step_id=step_id,
            step_name="complex-step",
            step_type="orchestrator",
            timeout_ms=60000,
            retry_count=5,
            enabled=True,
            skip_on_failure=True,
            continue_on_error=True,
            error_action="retry",
            max_memory_mb=2048,
            max_cpu_percent=80,
            priority=200,
            order_index=5,
            depends_on=depends_on,
            parallel_group="group-a",
            max_parallel_instances=4,
        )

        assert step.correlation_id == correlation_id
        assert step.step_id == step_id
        assert step.step_name == "complex-step"
        assert step.step_type == "orchestrator"
        assert step.timeout_ms == 60000
        assert step.retry_count == 5
        assert step.skip_on_failure is True
        assert step.continue_on_error is True
        assert step.error_action == "retry"
        assert step.max_memory_mb == 2048
        assert step.max_cpu_percent == 80
        assert step.priority == 200
        assert step.order_index == 5
        assert step.depends_on == depends_on
        assert step.parallel_group == "group-a"
        assert step.max_parallel_instances == 4

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowStep is immutable after creation."""
        step = ModelWorkflowStep(
            step_name="process-data",
            step_type="compute",
        )

        with pytest.raises(ValidationError):
            step.step_name = "new-name"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStep(
                step_name="process-data",
                step_type="compute",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_step_name_length_bounds(self) -> None:
        """Verify step_name length constraints (min=1, max=200)."""
        # Valid step_name
        valid = ModelWorkflowStep(
            step_name="valid-name",
            step_type="compute",
        )
        assert valid.step_name == "valid-name"

        # Too short (must be >= 1)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="",
                step_type="compute",
            )

        # Too long (must be <= 200)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="x" * 201,
                step_type="compute",
            )

    def test_timeout_ms_bounds(self) -> None:
        """Verify timeout_ms constraints (ge=100, le=300000)."""
        # Valid timeout
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            timeout_ms=60000,
        )
        assert valid.timeout_ms == 60000

        # Too small (must be >= 100)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                timeout_ms=99,
            )

        # Too large (must be <= 300000)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                timeout_ms=300001,
            )

    def test_retry_count_bounds(self) -> None:
        """Verify retry_count constraints (ge=0, le=10)."""
        # Valid retry count
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            retry_count=5,
        )
        assert valid.retry_count == 5

        # Negative (must be >= 0)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                retry_count=-1,
            )

        # Too large (must be <= 10)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                retry_count=11,
            )

    def test_priority_bounds(self) -> None:
        """Verify priority constraints (ge=1, le=1000)."""
        # Valid priority
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            priority=500,
        )
        assert valid.priority == 500

        # Too small (must be >= 1)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                priority=0,
            )

        # Too large (must be <= 1000)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                priority=1001,
            )

    def test_max_parallel_instances_bounds(self) -> None:
        """Verify max_parallel_instances constraints (ge=1, le=100)."""
        # Valid value
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_parallel_instances=50,
        )
        assert valid.max_parallel_instances == 50

        # Too small (must be >= 1)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_parallel_instances=0,
            )

        # Too large (must be <= 100)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_parallel_instances=101,
            )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowStep.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowStep.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelWorkflowStep(
            step_name="original-step",
            step_type="compute",
            priority=100,
        )

        modified = original.model_copy(update={"priority": 200})

        assert original.priority == 100  # Original unchanged
        assert modified.priority == 200  # Copy has new value


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelCoordinationRulesHardening:
    """Tests for ModelCoordinationRules frozen and extra=forbid behavior."""

    def test_valid_instantiation(self) -> None:
        """Verify ModelCoordinationRules can be created with valid data."""
        rules = ModelCoordinationRules(
            version=DEFAULT_VERSION,
        )

        assert rules.version == DEFAULT_VERSION
        assert rules.synchronization_points == []  # Default
        assert rules.parallel_execution_allowed is True  # Default
        assert rules.failure_recovery_strategy == EnumFailureRecoveryStrategy.RETRY

    def test_valid_instantiation_with_custom_values(self) -> None:
        """Verify ModelCoordinationRules accepts custom values."""
        rules = ModelCoordinationRules(
            version=DEFAULT_VERSION,
            synchronization_points=["checkpoint-1", "checkpoint-2"],
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.ABORT,
        )

        assert rules.synchronization_points == ["checkpoint-1", "checkpoint-2"]
        assert rules.parallel_execution_allowed is False
        assert rules.failure_recovery_strategy == EnumFailureRecoveryStrategy.ABORT

    def test_is_frozen(self) -> None:
        """Verify ModelCoordinationRules is immutable after creation."""
        rules = ModelCoordinationRules(
            version=DEFAULT_VERSION,
        )

        with pytest.raises(ValidationError):
            rules.parallel_execution_allowed = False  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCoordinationRules(
                version=DEFAULT_VERSION,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelCoordinationRules.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelCoordinationRules.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelCoordinationRules(
            version=DEFAULT_VERSION,
            parallel_execution_allowed=True,
        )

        modified = original.model_copy(update={"parallel_execution_allowed": False})

        assert original.parallel_execution_allowed is True  # Original unchanged
        assert modified.parallel_execution_allowed is False  # Copy has new value

    def test_all_failure_recovery_strategies(self) -> None:
        """Verify all EnumFailureRecoveryStrategy values are accepted."""
        strategies = [
            EnumFailureRecoveryStrategy.RETRY,
            EnumFailureRecoveryStrategy.ROLLBACK,
            EnumFailureRecoveryStrategy.COMPENSATE,
            EnumFailureRecoveryStrategy.ABORT,
        ]

        for strategy in strategies:
            rules = ModelCoordinationRules(
                version=DEFAULT_VERSION,
                failure_recovery_strategy=strategy,
            )
            assert rules.failure_recovery_strategy == strategy


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelExecutionGraphHardening:
    """Tests for ModelExecutionGraph frozen and extra=forbid behavior."""

    def test_valid_instantiation(self) -> None:
        """Verify ModelExecutionGraph can be created with valid data."""
        graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
        )

        assert graph.version == DEFAULT_VERSION
        assert graph.nodes == []  # Default

    def test_valid_instantiation_with_nodes(self) -> None:
        """Verify ModelExecutionGraph accepts nodes."""
        node1 = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        node2 = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.TRANSFORMER,
        )

        graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[node1, node2],
        )

        assert len(graph.nodes) == 2
        assert graph.nodes[0].node_type == EnumNodeType.COMPUTE_GENERIC
        assert graph.nodes[1].node_type == EnumNodeType.TRANSFORMER

    def test_is_frozen(self) -> None:
        """Verify ModelExecutionGraph is immutable after creation."""
        graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
        )

        with pytest.raises(ValidationError):
            graph.version = ModelSemVer(major=2, minor=0, patch=0)  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionGraph(
                version=DEFAULT_VERSION,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelExecutionGraph.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelExecutionGraph.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )

        new_node = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        modified = original.model_copy(update={"nodes": [new_node]})

        assert original.nodes == []  # Original unchanged
        assert len(modified.nodes) == 1  # Copy has new value


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelWorkflowNodeHardening:
    """Tests for ModelWorkflowNode frozen and extra=forbid behavior."""

    def test_valid_instantiation(self) -> None:
        """Verify ModelWorkflowNode can be created with valid data."""
        node = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )

        assert node.version == DEFAULT_VERSION
        assert node.node_type == EnumNodeType.COMPUTE_GENERIC
        assert node.node_requirements == {}  # Default
        assert node.dependencies == []  # Default
        # node_id is auto-generated by uuid4

    def test_valid_instantiation_with_custom_values(self) -> None:
        """Verify ModelWorkflowNode accepts custom values."""
        node_id = uuid4()
        dep1 = uuid4()
        dep2 = uuid4()

        node = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_id=node_id,
            node_type=EnumNodeType.TRANSFORMER,
            node_requirements={"cpu": 2, "memory": "4GB"},
            dependencies=[dep1, dep2],
        )

        assert node.node_id == node_id
        assert node.node_type == EnumNodeType.TRANSFORMER
        assert node.node_requirements == {"cpu": 2, "memory": "4GB"}
        assert node.dependencies == [dep1, dep2]

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowNode is immutable after creation."""
        node = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )

        with pytest.raises(ValidationError):
            node.node_type = EnumNodeType.TRANSFORMER  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowNode(
                version=DEFAULT_VERSION,
                node_type=EnumNodeType.COMPUTE_GENERIC,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowNode.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowNode.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )

        modified = original.model_copy(update={"node_type": EnumNodeType.TRANSFORMER})

        assert original.node_type == EnumNodeType.COMPUTE_GENERIC  # Original unchanged
        assert modified.node_type == EnumNodeType.TRANSFORMER  # Copy has new value

    def test_various_node_types(self) -> None:
        """Verify various EnumNodeType values are accepted."""
        node_types = [
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.TRANSFORMER,
            EnumNodeType.AGGREGATOR,
            EnumNodeType.GATEWAY,
            EnumNodeType.VALIDATOR,
        ]

        for node_type in node_types:
            node = ModelWorkflowNode(
                version=DEFAULT_VERSION,
                node_type=node_type,
            )
            assert node.node_type == node_type
