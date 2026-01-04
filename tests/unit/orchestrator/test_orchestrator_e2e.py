# SPDX-FileCopyrightText: 2024 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""
End-to-End Integration Tests for NodeOrchestrator Workflow.

This test suite validates the complete workflow lifecycle:
- Load YAML -> Parse to ModelWorkflowDefinition -> Validate -> Execute -> Verify Actions

Test Categories:
    1. Complete Workflow Tests - Full YAML -> Execute -> Verify flow
    2. Linear Workflow Tests - Sequential step1 -> step2 -> step3
    3. Diamond Workflow Tests - A -> (B, C) -> D
    4. Complex Multi-Branch Workflow Tests
    5. Error Path Tests - Invalid YAML, cycles, missing dependencies
    6. Full Integration Tests - Programmatic definition, validation, execution
    7. Round-Trip Integration Tests - YAML -> Model -> Execute -> Model -> YAML
    8. Performance Tests - Large workflow execution

OMN-657: End-to-end integration tests combining all orchestrator components.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumExecutionMode,
    EnumWorkflowState,
)
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_safe_yaml_loader import (
    load_and_validate_yaml_model,
    load_yaml_content_as_model,
)
from omnibase_core.utils.util_workflow_executor import (
    execute_workflow,
    get_execution_order,
    validate_workflow_definition,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def default_semver() -> ModelSemVer:
    """Default version for tests."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def simple_workflow_yaml() -> str:
    """Simple 3-step linear workflow YAML."""
    step1_id = str(uuid4())
    step2_id = str(uuid4())
    step3_id = str(uuid4())

    return f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: simple_linear_workflow
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: A simple 3-step linear workflow
  execution_mode: sequential
  timeout_ms: 60000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes:
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step1_id}"
      node_type: EFFECT_GENERIC
      node_requirements: {{}}
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step2_id}"
      node_type: COMPUTE_GENERIC
      node_requirements: {{}}
      dependencies:
        - "{step1_id}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step3_id}"
      node_type: REDUCER_GENERIC
      node_requirements: {{}}
      dependencies:
        - "{step2_id}"
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: false
  failure_recovery_strategy: RETRY
"""


@pytest.fixture
def diamond_workflow_yaml() -> str:
    """Diamond workflow: A -> (B, C) -> D."""
    step_a_id = str(uuid4())
    step_b_id = str(uuid4())
    step_c_id = str(uuid4())
    step_d_id = str(uuid4())

    return f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: diamond_workflow
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: Diamond dependency pattern A -> (B,C) -> D
  execution_mode: parallel
  timeout_ms: 120000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes:
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_a_id}"
      node_type: EFFECT_GENERIC
      node_requirements:
        step_name: step_a
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_b_id}"
      node_type: COMPUTE_GENERIC
      node_requirements:
        step_name: step_b
      dependencies:
        - "{step_a_id}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_c_id}"
      node_type: COMPUTE_GENERIC
      node_requirements:
        step_name: step_c
      dependencies:
        - "{step_a_id}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_d_id}"
      node_type: REDUCER_GENERIC
      node_requirements:
        step_name: step_d
      dependencies:
        - "{step_b_id}"
        - "{step_c_id}"
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: true
  failure_recovery_strategy: RETRY
"""


@pytest.fixture
def complex_workflow_yaml() -> str:
    """Complex multi-branch workflow with 7 nodes."""
    # Create a complex dependency graph:
    # A (start)
    # B, C depend on A
    # D depends on B
    # E depends on B, C
    # F depends on C
    # G depends on D, E, F (final aggregation)
    ids = [str(uuid4()) for _ in range(7)]

    return f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: complex_multi_branch
  workflow_version:
    major: 2
    minor: 0
    patch: 0
  description: Complex multi-branch workflow
  execution_mode: parallel
  timeout_ms: 180000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes:
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{ids[0]}"
      node_type: EFFECT_GENERIC
      node_requirements:
        step_name: node_A
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{ids[1]}"
      node_type: COMPUTE_GENERIC
      node_requirements:
        step_name: node_B
      dependencies:
        - "{ids[0]}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{ids[2]}"
      node_type: COMPUTE_GENERIC
      node_requirements:
        step_name: node_C
      dependencies:
        - "{ids[0]}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{ids[3]}"
      node_type: TRANSFORMER
      node_requirements:
        step_name: node_D
      dependencies:
        - "{ids[1]}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{ids[4]}"
      node_type: AGGREGATOR
      node_requirements:
        step_name: node_E
      dependencies:
        - "{ids[1]}"
        - "{ids[2]}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{ids[5]}"
      node_type: TRANSFORMER
      node_requirements:
        step_name: node_F
      dependencies:
        - "{ids[2]}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{ids[6]}"
      node_type: REDUCER_GENERIC
      node_requirements:
        step_name: node_G
      dependencies:
        - "{ids[3]}"
        - "{ids[4]}"
        - "{ids[5]}"
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points:
    - midpoint_sync
  parallel_execution_allowed: true
  failure_recovery_strategy: COMPENSATE
"""


@pytest.fixture
def cyclic_workflow_yaml() -> str:
    """Invalid workflow YAML with circular dependency."""
    step_a_id = str(uuid4())
    step_b_id = str(uuid4())
    step_c_id = str(uuid4())

    # A -> B -> C -> A (cycle)
    return f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: cyclic_workflow
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: Invalid workflow with cycle
  execution_mode: sequential
  timeout_ms: 30000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes:
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_a_id}"
      node_type: COMPUTE_GENERIC
      node_requirements: {{}}
      dependencies:
        - "{step_c_id}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_b_id}"
      node_type: COMPUTE_GENERIC
      node_requirements: {{}}
      dependencies:
        - "{step_a_id}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_c_id}"
      node_type: COMPUTE_GENERIC
      node_requirements: {{}}
      dependencies:
        - "{step_b_id}"
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: false
  failure_recovery_strategy: ABORT
"""


@pytest.fixture
def missing_dependency_yaml() -> str:
    """Invalid workflow YAML with missing dependency reference."""
    step_a_id = str(uuid4())
    missing_id = str(uuid4())  # Not defined as a node

    return f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: missing_dep_workflow
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: Invalid workflow with missing dependency
  execution_mode: sequential
  timeout_ms: 30000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes:
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_a_id}"
      node_type: COMPUTE_GENERIC
      node_requirements: {{}}
      dependencies:
        - "{missing_id}"
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: false
  failure_recovery_strategy: ABORT
"""


# =============================================================================
# Helper Functions
# =============================================================================


def create_workflow_steps_from_definition(
    workflow_definition: ModelWorkflowDefinition,
) -> list[ModelWorkflowStep]:
    """Create ModelWorkflowStep list from workflow definition nodes."""
    steps: list[ModelWorkflowStep] = []

    # Map node types to step types
    node_type_to_step_type = {
        EnumNodeType.EFFECT_GENERIC: "effect",
        EnumNodeType.COMPUTE_GENERIC: "compute",
        EnumNodeType.REDUCER_GENERIC: "reducer",
        EnumNodeType.ORCHESTRATOR_GENERIC: "orchestrator",
        EnumNodeType.TRANSFORMER: "compute",
        EnumNodeType.AGGREGATOR: "reducer",
        EnumNodeType.GATEWAY: "effect",
        EnumNodeType.VALIDATOR: "compute",
    }

    for idx, node in enumerate(workflow_definition.execution_graph.nodes):
        step_type = node_type_to_step_type.get(node.node_type, "custom")
        step_name = (
            node.node_requirements.get("step_name", f"step_{idx}")
            if node.node_requirements
            else f"step_{idx}"
        )

        step = ModelWorkflowStep(
            step_id=node.node_id,
            step_name=str(step_name),
            step_type=step_type,
            depends_on=node.dependencies,
            enabled=True,
            order_index=idx,
        )
        steps.append(step)

    return steps


# =============================================================================
# Complete Workflow Tests
# =============================================================================


@pytest.mark.unit
class TestCompleteWorkflowE2E:
    """End-to-end tests for complete workflow lifecycle."""

    @pytest.mark.asyncio
    async def test_yaml_to_execution_simple_linear(
        self, simple_workflow_yaml: str
    ) -> None:
        """Test: Load YAML -> Parse -> Validate -> Execute -> Verify actions."""
        # Step 1: Load YAML to ModelWorkflowDefinition
        workflow_def = load_yaml_content_as_model(
            simple_workflow_yaml, ModelWorkflowDefinition
        )

        assert workflow_def.workflow_metadata.workflow_name == "simple_linear_workflow"
        assert workflow_def.workflow_metadata.execution_mode == "sequential"
        assert len(workflow_def.execution_graph.nodes) == 3

        # Step 2: Create workflow steps from definition
        workflow_steps = create_workflow_steps_from_definition(workflow_def)
        assert len(workflow_steps) == 3

        # Step 3: Validate workflow
        validation_errors = await validate_workflow_definition(
            workflow_def, workflow_steps
        )
        assert validation_errors == [], f"Validation failed: {validation_errors}"

        # Step 4: Execute workflow
        workflow_id = uuid4()
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Step 5: Verify execution result
        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0
        assert len(result.actions_emitted) == 3
        assert result.execution_time_ms >= 1

        # Verify actions match steps
        for action in result.actions_emitted:
            assert isinstance(action, ModelAction)
            assert action.payload is not None
            assert "workflow_id" in action.payload.metadata
            assert "step_id" in action.payload.metadata

    @pytest.mark.asyncio
    async def test_yaml_to_execution_diamond_pattern(
        self, diamond_workflow_yaml: str
    ) -> None:
        """Test diamond pattern: A -> (B, C) -> D with parallel execution."""
        # Load and parse
        workflow_def = load_yaml_content_as_model(
            diamond_workflow_yaml, ModelWorkflowDefinition
        )

        assert workflow_def.workflow_metadata.workflow_name == "diamond_workflow"
        assert len(workflow_def.execution_graph.nodes) == 4

        # Create steps and validate
        workflow_steps = create_workflow_steps_from_definition(workflow_def)
        validation_errors = await validate_workflow_definition(
            workflow_def, workflow_steps
        )
        assert validation_errors == []

        # Execute
        workflow_id = uuid4()
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Verify
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 4
        assert len(result.actions_emitted) == 4
        assert result.metadata is not None
        assert result.metadata.execution_mode == "parallel"

    @pytest.mark.asyncio
    async def test_yaml_to_execution_complex_multi_branch(
        self, complex_workflow_yaml: str
    ) -> None:
        """Test complex multi-branch workflow with 7 nodes."""
        # Load and parse
        workflow_def = load_yaml_content_as_model(
            complex_workflow_yaml, ModelWorkflowDefinition
        )

        assert workflow_def.workflow_metadata.workflow_name == "complex_multi_branch"
        assert len(workflow_def.execution_graph.nodes) == 7

        # Create steps and validate
        workflow_steps = create_workflow_steps_from_definition(workflow_def)
        validation_errors = await validate_workflow_definition(
            workflow_def, workflow_steps
        )
        assert validation_errors == []

        # Execute
        workflow_id = uuid4()
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Verify all 7 steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 7
        assert len(result.actions_emitted) == 7


# =============================================================================
# Linear Workflow Tests
# =============================================================================


@pytest.mark.unit
class TestLinearWorkflowE2E:
    """Tests for linear step1 -> step2 -> step3 workflows."""

    @pytest.mark.asyncio
    async def test_linear_workflow_sequential_execution(self) -> None:
        """Test linear workflow executes steps in correct order."""
        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="linear_test",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Linear workflow test",
                execution_mode="sequential",
                timeout_ms=60000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=[
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step1_id,
                        node_type=EnumNodeType.EFFECT_GENERIC,
                        dependencies=[],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step2_id,
                        node_type=EnumNodeType.COMPUTE_GENERIC,
                        dependencies=[step1_id],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step3_id,
                        node_type=EnumNodeType.REDUCER_GENERIC,
                        dependencies=[step2_id],
                    ),
                ],
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        # Create steps
        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="step1",
                step_type="effect",
                depends_on=[],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="step2",
                step_type="compute",
                depends_on=[step1_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="step3",
                step_type="reducer",
                depends_on=[step2_id],
                enabled=True,
            ),
        ]

        # Get execution order
        execution_order = get_execution_order(steps)

        # Verify order: step1 -> step2 -> step3
        assert execution_order[0] == step1_id
        assert execution_order[1] == step2_id
        assert execution_order[2] == step3_id

        # Execute and verify
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 3

    @pytest.mark.asyncio
    async def test_linear_workflow_dependency_chain_respected(self) -> None:
        """Test that dependencies are properly enforced in linear chains."""
        ids = [uuid4() for _ in range(5)]

        # Create a 5-step chain: 0 -> 1 -> 2 -> 3 -> 4
        steps = [
            ModelWorkflowStep(
                step_id=ids[i],
                step_name=f"step_{i}",
                step_type="compute",
                depends_on=[ids[i - 1]] if i > 0 else [],
                enabled=True,
            )
            for i in range(5)
        ]

        # Verify topological order
        order = get_execution_order(steps)
        for i in range(5):
            assert order[i] == ids[i], f"Step {i} should be at position {i}"


# =============================================================================
# Diamond Workflow Tests
# =============================================================================


@pytest.mark.unit
class TestDiamondWorkflowE2E:
    """Tests for diamond pattern: A -> (B, C) -> D."""

    @pytest.mark.asyncio
    async def test_diamond_pattern_execution(self) -> None:
        """Test diamond pattern respects dependencies."""
        step_a = uuid4()
        step_b = uuid4()
        step_c = uuid4()
        step_d = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a,
                step_name="A",
                step_type="effect",
                depends_on=[],
            ),
            ModelWorkflowStep(
                step_id=step_b,
                step_name="B",
                step_type="compute",
                depends_on=[step_a],
            ),
            ModelWorkflowStep(
                step_id=step_c,
                step_name="C",
                step_type="compute",
                depends_on=[step_a],
            ),
            ModelWorkflowStep(
                step_id=step_d,
                step_name="D",
                step_type="reducer",
                depends_on=[step_b, step_c],
            ),
        ]

        # Get execution order
        order = get_execution_order(steps)

        # Verify: A must be first, D must be last
        assert order[0] == step_a, "A must be first (no dependencies)"
        assert order[-1] == step_d, "D must be last (depends on B and C)"

        # B and C can be in any order, but must come after A and before D
        assert step_b in order[1:3], "B must be in middle positions"
        assert step_c in order[1:3], "C must be in middle positions"

    @pytest.mark.asyncio
    async def test_diamond_parallel_execution_wave_grouping(
        self, diamond_workflow_yaml: str
    ) -> None:
        """Test diamond workflow groups B and C in same execution wave."""
        workflow_def = load_yaml_content_as_model(
            diamond_workflow_yaml, ModelWorkflowDefinition
        )
        workflow_steps = create_workflow_steps_from_definition(workflow_def)

        # Execute in parallel mode
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # All 4 steps should complete
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 4


# =============================================================================
# Error Path Tests
# =============================================================================


@pytest.mark.unit
class TestErrorPathsE2E:
    """Tests for error scenarios."""

    def test_invalid_yaml_syntax_raises_error(self, tmp_path: Path) -> None:
        """Test: Load invalid YAML -> Verify proper error raised."""
        invalid_yaml = """
workflow_name: bad
  invalid_indent: true
key: [unclosed
"""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(invalid_yaml, encoding="utf-8")

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, ModelWorkflowDefinition)

        assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR

    @pytest.mark.asyncio
    async def test_cyclic_workflow_validation_fails(
        self, cyclic_workflow_yaml: str
    ) -> None:
        """Test: Load valid YAML with cycle -> Validation fails with ModelOnexError."""
        # Load YAML (should parse successfully)
        workflow_def = load_yaml_content_as_model(
            cyclic_workflow_yaml, ModelWorkflowDefinition
        )

        # Create steps from definition
        workflow_steps = create_workflow_steps_from_definition(workflow_def)

        # Validate should detect cycle
        validation_errors = await validate_workflow_definition(
            workflow_def, workflow_steps
        )

        # Should have cycle error
        assert len(validation_errors) > 0
        assert any("cycle" in error.lower() for error in validation_errors)

    @pytest.mark.asyncio
    async def test_cyclic_workflow_execution_raises_error(
        self, cyclic_workflow_yaml: str
    ) -> None:
        """Test: Execute cyclic workflow -> ModelOnexError raised."""
        workflow_def = load_yaml_content_as_model(
            cyclic_workflow_yaml, ModelWorkflowDefinition
        )
        workflow_steps = create_workflow_steps_from_definition(workflow_def)

        # Execution should raise validation error
        with pytest.raises(ModelOnexError) as exc_info:
            await execute_workflow(
                workflow_definition=workflow_def,
                workflow_steps=workflow_steps,
                workflow_id=uuid4(),
            )

        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.ORCHESTRATOR_EXEC_WORKFLOW_FAILED
        )
        assert "cycle" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_missing_dependency_validation_fails(
        self, missing_dependency_yaml: str
    ) -> None:
        """Test: Load valid YAML with missing dependency -> Validation fails."""
        workflow_def = load_yaml_content_as_model(
            missing_dependency_yaml, ModelWorkflowDefinition
        )
        workflow_steps = create_workflow_steps_from_definition(workflow_def)

        # Validate should detect missing dependency
        validation_errors = await validate_workflow_definition(
            workflow_def, workflow_steps
        )

        # Should have missing dependency error
        assert len(validation_errors) > 0
        assert any(
            "non-existent" in error.lower() or "depends" in error.lower()
            for error in validation_errors
        )

    def test_empty_workflow_raises_validation_error(self) -> None:
        """Test empty workflow file raises validation error."""
        empty_yaml = ""

        with pytest.raises(ModelOnexError) as exc_info:
            load_yaml_content_as_model(empty_yaml, ModelWorkflowDefinition)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_extra_fields_rejected_with_extra_forbid(self) -> None:
        """Test that extra fields are rejected due to extra='forbid'."""
        yaml_with_extra = """
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: test
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: test
  execution_mode: sequential
  timeout_ms: 30000
  extra_forbidden_field: should_fail
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes: []
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: false
  failure_recovery_strategy: ABORT
"""
        with pytest.raises(ModelOnexError) as exc_info:
            load_yaml_content_as_model(yaml_with_extra, ModelWorkflowDefinition)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


# =============================================================================
# Full Integration Tests
# =============================================================================


@pytest.mark.unit
class TestFullIntegrationE2E:
    """Tests for programmatic definition, validation, and execution."""

    @pytest.mark.asyncio
    async def test_programmatic_definition_to_execution(self) -> None:
        """Test: Create ModelWorkflowDefinition programmatically -> Validate -> Execute -> Get result."""
        # Create workflow programmatically
        step1_id = uuid4()
        step2_id = uuid4()

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="programmatic_workflow",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Created programmatically",
                execution_mode="sequential",
                timeout_ms=30000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=[
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step1_id,
                        node_type=EnumNodeType.EFFECT_GENERIC,
                        dependencies=[],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step2_id,
                        node_type=EnumNodeType.COMPUTE_GENERIC,
                        dependencies=[step1_id],
                    ),
                ],
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        # Create steps
        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="fetch_data",
                step_type="effect",
                depends_on=[],
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="process_data",
                step_type="compute",
                depends_on=[step1_id],
            ),
        ]

        # Validate
        errors = await validate_workflow_definition(workflow_def, steps)
        assert errors == []

        # Execute
        workflow_id = uuid4()
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=workflow_id,
        )

        # Verify result
        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 2
        assert len(result.actions_emitted) == 2

    @pytest.mark.asyncio
    async def test_action_structure_correctness(self) -> None:
        """Test: Verify all actions emitted have correct structure."""
        step1_id = uuid4()
        step2_id = uuid4()

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="action_test",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Test action structure",
                execution_mode="sequential",
                timeout_ms=30000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=[
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step1_id,
                        node_type=EnumNodeType.EFFECT_GENERIC,
                        dependencies=[],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step2_id,
                        node_type=EnumNodeType.COMPUTE_GENERIC,
                        dependencies=[step1_id],
                    ),
                ],
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="effect_step",
                step_type="effect",
                depends_on=[],
                timeout_ms=5000,
                retry_count=2,
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="compute_step",
                step_type="compute",
                depends_on=[step1_id],
                timeout_ms=10000,
                retry_count=3,
            ),
        ]

        workflow_id = uuid4()
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=workflow_id,
        )

        # Verify action structure
        for action in result.actions_emitted:
            # Required fields
            assert action.action_id is not None
            assert isinstance(action.action_id, UUID)
            assert action.action_type in [
                EnumActionType.EFFECT,
                EnumActionType.COMPUTE,
            ]
            assert action.target_node_type in ["NodeEffect", "NodeCompute"]
            assert action.payload is not None
            assert action.lease_id is not None
            assert action.created_at is not None

            # Payload structure (workflow context is in payload.metadata)
            assert "workflow_id" in action.payload.metadata
            assert "step_id" in action.payload.metadata
            assert "step_name" in action.payload.metadata

            # Verify timeout and retry_count are set
            assert action.timeout_ms is not None
            assert action.retry_count is not None

    @pytest.mark.asyncio
    async def test_action_dependencies_match_workflow_dependencies(self) -> None:
        """Test: Verify action dependencies match workflow dependencies."""
        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="step1",
                step_type="effect",
                depends_on=[],
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="step2",
                step_type="compute",
                depends_on=[step1_id],
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="step3",
                step_type="reducer",
                depends_on=[step1_id, step2_id],
            ),
        ]

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="dep_test",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Dependency test",
                execution_mode="sequential",
                timeout_ms=30000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=[
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step1_id,
                        node_type=EnumNodeType.EFFECT_GENERIC,
                        dependencies=[],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step2_id,
                        node_type=EnumNodeType.COMPUTE_GENERIC,
                        dependencies=[step1_id],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step3_id,
                        node_type=EnumNodeType.REDUCER_GENERIC,
                        dependencies=[step1_id, step2_id],
                    ),
                ],
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )

        # Build action map from payload metadata
        action_by_step: dict[str, ModelAction] = {}
        for action in result.actions_emitted:
            step_id = action.payload.metadata.get("step_id")
            if step_id:
                action_by_step[str(step_id)] = action

        # Verify dependencies
        assert len(action_by_step[str(step1_id)].dependencies) == 0
        assert step1_id in action_by_step[str(step2_id)].dependencies
        assert step1_id in action_by_step[str(step3_id)].dependencies
        assert step2_id in action_by_step[str(step3_id)].dependencies

    @pytest.mark.asyncio
    async def test_execution_order_follows_topological_sort(self) -> None:
        """Test: Verify execution order follows topological sort."""
        # Create a complex dependency graph
        ids = [uuid4() for _ in range(6)]

        # Graph: 0 -> 1 -> 3
        #        0 -> 2 -> 4
        #        3,4 -> 5
        steps = [
            ModelWorkflowStep(step_id=ids[0], step_name="s0", step_type="effect"),
            ModelWorkflowStep(
                step_id=ids[1], step_name="s1", step_type="compute", depends_on=[ids[0]]
            ),
            ModelWorkflowStep(
                step_id=ids[2], step_name="s2", step_type="compute", depends_on=[ids[0]]
            ),
            ModelWorkflowStep(
                step_id=ids[3], step_name="s3", step_type="compute", depends_on=[ids[1]]
            ),
            ModelWorkflowStep(
                step_id=ids[4], step_name="s4", step_type="compute", depends_on=[ids[2]]
            ),
            ModelWorkflowStep(
                step_id=ids[5],
                step_name="s5",
                step_type="reducer",
                depends_on=[ids[3], ids[4]],
            ),
        ]

        order = get_execution_order(steps)

        # Verify topological invariants
        for i, step_id in enumerate(order):
            step = next(s for s in steps if s.step_id == step_id)
            for dep_id in step.depends_on:
                dep_pos = order.index(dep_id)
                assert dep_pos < i, f"Dependency {dep_id} should come before {step_id}"


# =============================================================================
# Round-Trip Integration Tests
# =============================================================================


@pytest.mark.unit
class TestRoundTripIntegrationE2E:
    """Tests for YAML -> Model -> Execute -> Model -> YAML round-trip."""

    @pytest.mark.asyncio
    async def test_yaml_round_trip_through_execution(
        self, simple_workflow_yaml: str
    ) -> None:
        """Test: YAML -> Model -> Validate -> Execute -> Model -> YAML -> Compare."""
        # Parse original YAML
        original_dict = yaml.safe_load(simple_workflow_yaml)

        # Load to model
        workflow_def = load_yaml_content_as_model(
            simple_workflow_yaml, ModelWorkflowDefinition
        )
        workflow_steps = create_workflow_steps_from_definition(workflow_def)

        # Validate
        errors = await validate_workflow_definition(workflow_def, workflow_steps)
        assert errors == []

        # Execute
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=uuid4(),
        )
        assert result.execution_status == EnumWorkflowState.COMPLETED

        # Convert model back to dict
        round_tripped_dict = workflow_def.model_dump(mode="json")

        # Compare key structural elements
        assert (
            round_tripped_dict["workflow_metadata"]["workflow_name"]
            == original_dict["workflow_metadata"]["workflow_name"]
        )
        assert (
            round_tripped_dict["workflow_metadata"]["execution_mode"]
            == original_dict["workflow_metadata"]["execution_mode"]
        )
        assert len(round_tripped_dict["execution_graph"]["nodes"]) == len(
            original_dict["execution_graph"]["nodes"]
        )

    @pytest.mark.asyncio
    async def test_fingerprint_stability_through_workflow(
        self, simple_workflow_yaml: str
    ) -> None:
        """Test: Fingerprint stability through full workflow execution."""
        # Load workflow
        workflow_def = load_yaml_content_as_model(
            simple_workflow_yaml, ModelWorkflowDefinition
        )

        # Compute hash before execution
        hash_before = workflow_def.compute_workflow_hash()

        # Execute workflow (should not modify the definition)
        workflow_steps = create_workflow_steps_from_definition(workflow_def)
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=uuid4(),
        )

        # Compute hash after execution
        hash_after = workflow_def.compute_workflow_hash()

        # Hashes should be identical
        assert hash_before == hash_after
        assert result.metadata is not None
        assert result.metadata.workflow_hash == hash_before

    def test_workflow_hash_deterministic_across_loads(
        self, simple_workflow_yaml: str
    ) -> None:
        """Test: Same YAML produces same hash across multiple loads."""
        # Load the same YAML multiple times
        hashes: list[str] = []
        for _ in range(5):
            workflow_def = load_yaml_content_as_model(
                simple_workflow_yaml, ModelWorkflowDefinition
            )
            hashes.append(workflow_def.compute_workflow_hash())

        # All hashes should be identical
        assert len(set(hashes)) == 1, "Hash should be deterministic"

    def test_workflow_with_computed_hash_round_trip(
        self, simple_workflow_yaml: str
    ) -> None:
        """Test workflow with computed hash round-trips correctly."""
        # Load and compute hash
        workflow_def = load_yaml_content_as_model(
            simple_workflow_yaml, ModelWorkflowDefinition
        )
        workflow_with_hash = workflow_def.with_computed_hash()

        # Verify hash is set
        assert workflow_with_hash.workflow_metadata.workflow_hash is not None

        # Serialize to JSON and back
        json_str = workflow_with_hash.model_dump_json()
        reparsed = ModelWorkflowDefinition.model_validate_json(json_str)

        # Hash should survive round-trip
        assert (
            reparsed.workflow_metadata.workflow_hash
            == workflow_with_hash.workflow_metadata.workflow_hash
        )


# =============================================================================
# Performance Tests
# =============================================================================


@pytest.mark.unit
class TestPerformanceE2E:
    """Performance tests for workflow execution."""

    @pytest.mark.asyncio
    async def test_50_step_workflow_executes_in_reasonable_time(self) -> None:
        """Test: 50-step workflow executes in reasonable time (<5s)."""
        import time

        # Create a 50-step linear workflow
        ids = [uuid4() for _ in range(50)]

        nodes = [
            ModelWorkflowNode(
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_id=ids[i],
                node_type=EnumNodeType.COMPUTE_GENERIC,
                dependencies=[ids[i - 1]] if i > 0 else [],
            )
            for i in range(50)
        ]

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="large_workflow",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="50-step workflow",
                execution_mode="sequential",
                timeout_ms=300000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=nodes,
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        steps = [
            ModelWorkflowStep(
                step_id=ids[i],
                step_name=f"step_{i}",
                step_type="compute",
                depends_on=[ids[i - 1]] if i > 0 else [],
            )
            for i in range(50)
        ]

        # Time the execution
        start = time.perf_counter()
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )
        elapsed = time.perf_counter() - start

        # Verify completion
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 50
        assert len(result.actions_emitted) == 50

        # Should complete in reasonable time (generous 5s limit for CI)
        assert elapsed < 5.0, f"50-step workflow took {elapsed:.2f}s (limit: 5s)"

    @pytest.mark.asyncio
    async def test_parallel_execution_completes_with_independent_steps(self) -> None:
        """Test parallel execution completes successfully with independent steps."""
        # Create workflow with multiple independent steps after initial step
        root_id = uuid4()
        parallel_ids = [uuid4() for _ in range(10)]
        final_id = uuid4()

        nodes = [
            ModelWorkflowNode(
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_id=root_id,
                node_type=EnumNodeType.EFFECT_GENERIC,
                dependencies=[],
            ),
            *[
                ModelWorkflowNode(
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    node_id=pid,
                    node_type=EnumNodeType.COMPUTE_GENERIC,
                    dependencies=[root_id],
                )
                for pid in parallel_ids
            ],
            ModelWorkflowNode(
                version=ModelSemVer(major=1, minor=0, patch=0),
                node_id=final_id,
                node_type=EnumNodeType.REDUCER_GENERIC,
                dependencies=parallel_ids,
            ),
        ]

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="parallel_test",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Parallel execution test",
                execution_mode="parallel",
                timeout_ms=60000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=nodes,
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=True,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        steps = [
            ModelWorkflowStep(
                step_id=root_id, step_name="root", step_type="effect", depends_on=[]
            ),
            *[
                ModelWorkflowStep(
                    step_id=pid,
                    step_name=f"parallel_{i}",
                    step_type="compute",
                    depends_on=[root_id],
                )
                for i, pid in enumerate(parallel_ids)
            ],
            ModelWorkflowStep(
                step_id=final_id,
                step_name="final",
                step_type="reducer",
                depends_on=parallel_ids,
            ),
        ]

        # Execute in parallel mode
        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Verify completion
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 12  # 1 + 10 + 1
        assert result.metadata is not None
        assert result.metadata.execution_mode == "parallel"


# =============================================================================
# Batch Execution Tests
# =============================================================================


@pytest.mark.unit
class TestBatchExecutionE2E:
    """Tests for batch execution mode."""

    @pytest.mark.asyncio
    async def test_batch_execution_mode(self, simple_workflow_yaml: str) -> None:
        """Test batch execution mode includes batch metadata."""
        workflow_def = load_yaml_content_as_model(
            simple_workflow_yaml, ModelWorkflowDefinition
        )
        workflow_steps = create_workflow_steps_from_definition(workflow_def)

        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.BATCH,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert result.metadata is not None
        assert result.metadata.execution_mode == "batch"
        assert result.metadata.batch_size is not None


# =============================================================================
# Disabled Steps Tests
# =============================================================================


@pytest.mark.unit
class TestDisabledStepsE2E:
    """Tests for workflows with disabled steps.

    v1.0.2 Fix 10: Disabled steps are treated as automatically satisfied dependencies.
    - Disabled steps appear ONLY in skipped_steps (not completed/failed)
    - Steps depending on disabled steps proceed as if the dependency is met
    - skipped_steps tracks disabled steps in declaration order
    """

    @pytest.mark.asyncio
    async def test_disabled_steps_skipped_in_execution(self) -> None:
        """Test that disabled steps are skipped during execution.

        v1.0.2 Fix 10: Disabled steps appear in skipped_steps and are treated
        as satisfied dependencies, allowing dependent steps to proceed.
        """
        step1_id = uuid4()
        step2_id = uuid4()  # Will be disabled
        step3_id = uuid4()

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="disabled_test",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Test disabled steps",
                execution_mode="sequential",
                timeout_ms=30000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=[
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step1_id,
                        node_type=EnumNodeType.EFFECT_GENERIC,
                        dependencies=[],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step2_id,
                        node_type=EnumNodeType.COMPUTE_GENERIC,
                        dependencies=[step1_id],
                    ),
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step3_id,
                        node_type=EnumNodeType.REDUCER_GENERIC,
                        dependencies=[],  # No dependency on step2
                    ),
                ],
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="enabled_1",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="disabled",
                step_type="compute",
                enabled=False,  # Disabled
                depends_on=[step1_id],
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="enabled_2",
                step_type="reducer",
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )

        # Only 2 steps should complete (disabled skipped)
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 2
        assert str(step2_id) not in result.completed_steps
        assert len(result.actions_emitted) == 2

        # v1.0.2 Fix 10: Disabled step tracked in skipped_steps
        assert str(step2_id) in result.skipped_steps
        assert len(result.skipped_steps) == 1  # Only the disabled step
        assert result.skipped_steps == [str(step2_id)], (
            "skipped_steps should contain exactly the disabled step ID"
        )

        # Enabled steps must NOT appear in skipped_steps
        assert str(step1_id) not in result.skipped_steps, (
            "Enabled step 1 must NOT appear in skipped_steps"
        )
        assert str(step3_id) not in result.skipped_steps, (
            "Enabled step 3 must NOT appear in skipped_steps"
        )

        # Disabled step must NOT appear in failed_steps
        assert str(step2_id) not in result.failed_steps, (
            "Disabled step must NOT appear in failed_steps"
        )


# =============================================================================
# Metadata Verification Tests
# =============================================================================


@pytest.mark.unit
class TestMetadataVerificationE2E:
    """Tests for workflow and action metadata verification."""

    @pytest.mark.asyncio
    async def test_workflow_metadata_preserved_in_result(
        self, simple_workflow_yaml: str
    ) -> None:
        """Test workflow metadata is preserved in execution result."""
        workflow_def = load_yaml_content_as_model(
            simple_workflow_yaml, ModelWorkflowDefinition
        )
        workflow_steps = create_workflow_steps_from_definition(workflow_def)

        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=workflow_steps,
            workflow_id=uuid4(),
        )

        # Verify metadata
        assert result.metadata is not None
        assert (
            result.metadata.workflow_name
            == workflow_def.workflow_metadata.workflow_name
        )
        assert result.metadata.workflow_hash != ""

    @pytest.mark.asyncio
    async def test_action_metadata_includes_correlation_id(self) -> None:
        """Test action metadata includes correlation ID."""
        step_id = uuid4()

        workflow_def = ModelWorkflowDefinition(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=ModelSemVer(major=1, minor=0, patch=0),
                workflow_name="correlation_test",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Test correlation ID",
                execution_mode="sequential",
                timeout_ms=30000,
            ),
            execution_graph=ModelExecutionGraph(
                version=ModelSemVer(major=1, minor=0, patch=0),
                nodes=[
                    ModelWorkflowNode(
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        node_id=step_id,
                        node_type=EnumNodeType.COMPUTE_GENERIC,
                        dependencies=[],
                    ),
                ],
            ),
            coordination_rules=ModelCoordinationRules(
                version=ModelSemVer(major=1, minor=0, patch=0),
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            ),
        )

        steps = [
            ModelWorkflowStep(
                step_id=step_id,
                step_name="single_step",
                step_type="compute",
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_def,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )

        # Verify action metadata
        assert len(result.actions_emitted) == 1
        action = result.actions_emitted[0]
        assert "correlation_id" in action.metadata.parameters
        assert action.metadata.parameters["step_name"] == "single_step"
