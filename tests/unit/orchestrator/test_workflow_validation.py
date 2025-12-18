# SPDX-FileCopyrightText: 2025 OmniNode AI
# SPDX-License-Identifier: Apache-2.0

"""
MVP Conformance Tests: NodeOrchestrator Workflow Validation [OMN-657].

This module provides comprehensive validation tests for the workflow validation
functions in `omnibase_core.utils.workflow_executor`. These tests ensure the
NodeOrchestrator correctly validates workflow definitions before execution.

Test Categories:
    - Cycle Detection: Validates detection of circular dependencies in workflow graphs
    - Dependency Validation: Ensures all step dependencies reference existing steps
    - Duplicate Step Validation: Tests uniqueness constraints on step IDs
    - Invariant Enforcement: Validates execution mode and workflow constraints
    - Error Message Quality: Ensures validation errors contain useful debugging info
    - Edge Cases: Tests boundary conditions and large workflow handling

Reference:
    - Source module: omnibase_core.utils.workflow_executor
    - Architecture: docs/architecture/CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md
    - Ticket: OMN-657 (MVP Conformance Tests)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.workflow_executor import (
    get_execution_order,
    validate_workflow_definition,
)

# ============================================================================
# Fixtures
# ============================================================================
#
# Fixture Design Rationale (PR #160 Review):
# ------------------------------------------
# The current fixture set is intentionally minimal and well-scoped:
#
# 1. base_workflow_definition / parallel_workflow_definition:
#    Cover the two primary workflow types (sequential, parallel) used across tests.
#
# 2. create_step() helper:
#    Factory function with sensible defaults - preferred over multiple fixtures
#    because it allows tests to specify only the parameters they care about.
#
# 3. Inline test data (UUIDs, step configurations):
#    Kept inline deliberately because:
#    - Makes each test self-documenting (shows exactly what's being tested)
#    - Prevents hidden coupling between tests
#    - UUIDs should be unique per test for proper isolation
#
# Patterns NOT extracted to fixtures (by design):
# - Cycle patterns: Test-specific configurations are clearer inline
# - Execution modes: Use parameterization when needed, not fixtures
# - Complex graphs: Single-use patterns don't benefit from extraction
#
# If adding new test patterns that repeat 3+ times, consider adding a fixture.
# ============================================================================


@pytest.fixture
def base_workflow_definition() -> ModelWorkflowDefinition:
    """Create base workflow definition for testing."""
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="test_validation_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Workflow for validation testing",
            execution_mode="sequential",
            timeout_ms=60000,
        ),
        execution_graph=ModelExecutionGraph(
            nodes=[],
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        version=ModelSemVer(major=1, minor=0, patch=0),
    )


@pytest.fixture
def parallel_workflow_definition() -> ModelWorkflowDefinition:
    """Create parallel workflow definition for testing."""
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="test_parallel_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Parallel workflow for validation testing",
            execution_mode="parallel",
            timeout_ms=120000,
        ),
        execution_graph=ModelExecutionGraph(
            nodes=[],
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=True,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        version=ModelSemVer(major=1, minor=0, patch=0),
    )


def create_step(
    step_id: UUID | None = None,
    step_name: str = "Test Step",
    step_type: Literal[
        "compute",
        "effect",
        "reducer",
        "orchestrator",
        "conditional",
        "parallel",
        "custom",
    ] = "compute",
    depends_on: list[UUID] | None = None,
    enabled: bool = True,
) -> ModelWorkflowStep:
    """Helper factory function to create workflow steps."""
    return ModelWorkflowStep(
        step_id=step_id or uuid4(),
        step_name=step_name,
        step_type=step_type,
        depends_on=depends_on or [],
        enabled=enabled,
    )


# ============================================================================
# Cycle Detection Tests
# ============================================================================


@pytest.mark.unit
class TestCycleDetection:
    """Test cycle detection in workflow dependency graphs."""

    @pytest.mark.asyncio
    async def test_simple_cycle_a_to_b_to_a(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test detection of simple two-node cycle (A -> B -> A)."""
        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[step_b_id],  # A depends on B
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id],  # B depends on A - CYCLE
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0, "Should detect cycle"
        assert any("cycle" in error.lower() for error in errors), (
            f"Error should mention 'cycle': {errors}"
        )

    @pytest.mark.asyncio
    async def test_complex_cycle_a_to_b_to_c_to_a(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test detection of complex three-node cycle (A -> B -> C -> A)."""
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[step_c_id],  # A depends on C
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id],  # B depends on A
            ),
            create_step(
                step_id=step_c_id,
                step_name="Step C",
                depends_on=[step_b_id],  # C depends on B - completes CYCLE
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0, "Should detect complex cycle"
        assert any("cycle" in error.lower() for error in errors), (
            f"Error should mention 'cycle': {errors}"
        )

    @pytest.mark.asyncio
    async def test_self_referencing_step(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test detection of self-referencing step (A -> A)."""
        step_a_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[step_a_id],  # A depends on itself - SELF CYCLE
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0, "Should detect self-referencing cycle"
        assert any("cycle" in error.lower() for error in errors), (
            f"Error should mention 'cycle': {errors}"
        )

    @pytest.mark.asyncio
    async def test_valid_dag_no_cycles(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that valid DAG passes validation (no false positives)."""
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        # Linear dependency: A <- B <- C
        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[],  # No dependencies
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id],  # B depends on A
            ),
            create_step(
                step_id=step_c_id,
                step_name="Step C",
                depends_on=[step_b_id],  # C depends on B
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Filter out non-cycle errors (there might be other validation)
        cycle_errors = [e for e in errors if "cycle" in e.lower()]
        assert len(cycle_errors) == 0, (
            f"Should not detect cycles in valid DAG: {errors}"
        )

    @pytest.mark.asyncio
    async def test_diamond_pattern_passes(
        self, parallel_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that diamond dependency pattern passes (A -> B,C -> D).

        Diamond pattern:
            A
           / \
          B   C
           \\ /
            D
        """
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()
        step_d_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[],
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id],  # B depends on A
            ),
            create_step(
                step_id=step_c_id,
                step_name="Step C",
                depends_on=[step_a_id],  # C depends on A
            ),
            create_step(
                step_id=step_d_id,
                step_name="Step D",
                depends_on=[step_b_id, step_c_id],  # D depends on B and C
            ),
        ]

        errors = await validate_workflow_definition(parallel_workflow_definition, steps)

        cycle_errors = [e for e in errors if "cycle" in e.lower()]
        assert len(cycle_errors) == 0, (
            f"Diamond pattern should not be detected as cycle: {errors}"
        )

    def test_cycle_raises_error_in_get_execution_order(self) -> None:
        """Test that get_execution_order raises ModelOnexError for cycles."""
        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[step_b_id],
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id],
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            get_execution_order(steps)

        error = exc_info.value
        assert "cycle" in str(error).lower(), (
            f"Error message should mention cycle: {error}"
        )
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_indirect_cycle_detection(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test detection of indirect cycle through multiple nodes."""
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()
        step_d_id = uuid4()

        # A -> B -> C -> D -> B (cycle between B, C, D)
        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[],
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id, step_d_id],  # B depends on A and D
            ),
            create_step(
                step_id=step_c_id,
                step_name="Step C",
                depends_on=[step_b_id],  # C depends on B
            ),
            create_step(
                step_id=step_d_id,
                step_name="Step D",
                depends_on=[step_c_id],  # D depends on C - creates cycle B->C->D->B
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0, "Should detect indirect cycle"
        assert any("cycle" in error.lower() for error in errors), (
            f"Error should mention 'cycle': {errors}"
        )


# ============================================================================
# Dependency Validation Tests
# ============================================================================


@pytest.mark.unit
class TestDependencyValidation:
    """Test dependency reference validation in workflows."""

    @pytest.mark.asyncio
    async def test_missing_dependency_reference_raises_error(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that missing dependency reference is detected."""
        non_existent_id = uuid4()

        steps = [
            create_step(
                step_name="Step A",
                depends_on=[non_existent_id],  # References non-existent step
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0, "Should detect missing dependency"
        assert any("non-existent" in error.lower() for error in errors), (
            f"Error should mention 'non-existent': {errors}"
        )

    @pytest.mark.asyncio
    async def test_valid_dependencies_pass(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that valid dependencies pass validation."""
        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[],
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id],  # Valid dependency
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Filter out non-dependency errors
        dep_errors = [e for e in errors if "non-existent" in e.lower()]
        assert len(dep_errors) == 0, f"Valid dependencies should pass: {errors}"

    @pytest.mark.asyncio
    async def test_empty_depends_on_is_valid(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that empty depends_on list is valid."""
        steps = [
            create_step(
                step_name="Independent Step",
                depends_on=[],  # No dependencies
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        dep_errors = [e for e in errors if "depend" in e.lower()]
        assert len(dep_errors) == 0, f"Empty depends_on should be valid: {errors}"

    @pytest.mark.asyncio
    async def test_all_dependencies_must_exist(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that ALL dependencies must exist, not just some."""
        step_a_id = uuid4()
        non_existent_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[],
            ),
            create_step(
                step_name="Step B",
                depends_on=[step_a_id, non_existent_id],  # One valid, one invalid
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0, "Should detect missing dependency even with valid ones"
        assert any("non-existent" in error.lower() for error in errors), (
            f"Error should mention 'non-existent': {errors}"
        )

    @pytest.mark.asyncio
    async def test_multiple_missing_dependencies(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test detection of multiple missing dependencies."""
        non_existent_id_1 = uuid4()
        non_existent_id_2 = uuid4()

        steps = [
            create_step(
                step_name="Step A",
                depends_on=[non_existent_id_1],  # Missing dependency 1
            ),
            create_step(
                step_name="Step B",
                depends_on=[non_existent_id_2],  # Missing dependency 2
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Should have errors for both missing dependencies
        non_existent_errors = [e for e in errors if "non-existent" in e.lower()]
        assert len(non_existent_errors) >= 2, (
            f"Should detect both missing dependencies: {errors}"
        )


# ============================================================================
# Duplicate Step ID Tests
# ============================================================================


@pytest.mark.unit
class TestDuplicateStepValidation:
    """Test duplicate step ID detection in workflows.

    Note: ModelWorkflowStep uses frozen=True, so step_id uniqueness is not
    enforced at the model level. The validation must occur in workflow_executor.
    """

    @pytest.mark.asyncio
    async def test_unique_step_ids_pass(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that unique step IDs pass validation."""
        steps = [
            create_step(step_id=uuid4(), step_name="Step A"),
            create_step(step_id=uuid4(), step_name="Step B"),
            create_step(step_id=uuid4(), step_name="Step C"),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Filter out duplicate-related errors
        dup_errors = [e for e in errors if "duplicate" in e.lower()]
        assert len(dup_errors) == 0, f"Unique IDs should pass: {errors}"

    @pytest.mark.asyncio
    async def test_duplicate_step_names_allowed(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that duplicate step names are allowed (only IDs must be unique)."""
        steps = [
            create_step(step_id=uuid4(), step_name="Same Name"),
            create_step(
                step_id=uuid4(), step_name="Same Name"
            ),  # Same name, different ID
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Should not fail for duplicate names
        name_errors = [
            e for e in errors if "name" in e.lower() and "duplicate" in e.lower()
        ]
        assert len(name_errors) == 0, f"Duplicate names should be allowed: {errors}"

    @pytest.mark.asyncio
    async def test_duplicate_step_ids_detected(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that duplicate step IDs are detected during validation.

        Validates that validate_workflow_definition() correctly detects when
        two or more workflow steps share the same step_id. Duplicate step IDs
        violate workflow invariants because:
        1. Step IDs are used to track execution state and results
        2. Duplicate IDs cause ambiguity in step lookup and routing
        3. Workflow graphs rely on unique step IDs for dependency resolution

        The validation returns an error message that identifies the duplicate ID(s).
        """
        duplicate_id = uuid4()

        # SETUP: Create two steps with the SAME step_id but different names
        # This should be invalid - step IDs must be unique within a workflow
        steps = [
            create_step(step_id=duplicate_id, step_name="Step A"),
            create_step(step_id=duplicate_id, step_name="Step B"),  # Same ID!
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Validation should detect the duplicate step ID
        assert len(errors) > 0, "Should detect duplicate step IDs"
        # Error message should clearly indicate a duplicate was found
        assert any("duplicate" in error.lower() for error in errors), (
            f"Error should mention 'duplicate': {errors}"
        )


# ============================================================================
# Invariant Enforcement Tests
# ============================================================================


@pytest.mark.unit
class TestInvariantEnforcement:
    """Test workflow invariant enforcement.

    Tests validation of execution modes and workflow state constraints.
    """

    @pytest.mark.asyncio
    async def test_sequential_execution_mode_valid(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that sequential execution mode is valid."""
        steps = [
            create_step(step_name="Step A"),
            create_step(step_name="Step B"),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        mode_errors = [e for e in errors if "mode" in e.lower()]
        assert len(mode_errors) == 0, f"Sequential mode should be valid: {errors}"

    @pytest.mark.asyncio
    async def test_parallel_execution_mode_valid(
        self, parallel_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that parallel execution mode is valid."""
        steps = [
            create_step(step_name="Step A"),
            create_step(step_name="Step B"),
        ]

        errors = await validate_workflow_definition(parallel_workflow_definition, steps)

        mode_errors = [e for e in errors if "mode" in e.lower()]
        assert len(mode_errors) == 0, f"Parallel mode should be valid: {errors}"

    @pytest.mark.asyncio
    async def test_batch_execution_mode_valid(self) -> None:
        """Test that batch execution mode is valid."""
        workflow_def = ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="batch_workflow",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Batch workflow test",
                execution_mode="batch",
                timeout_ms=60000,
            ),
            execution_graph=ModelExecutionGraph(
                nodes=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            coordination_rules=ModelCoordinationRules(
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        steps = [create_step(step_name="Batch Step")]

        errors = await validate_workflow_definition(workflow_def, steps)

        mode_errors = [e for e in errors if "mode" in e.lower()]
        assert len(mode_errors) == 0, f"Batch mode should be valid: {errors}"

    @pytest.mark.asyncio
    async def test_conditional_execution_mode_rejected_in_v1(self) -> None:
        """Test that conditional execution mode is rejected in v1.0.

        CONDITIONAL mode is not supported in v1.0 workflow execution.
        """
        workflow_def = ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="conditional_workflow",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Conditional workflow test",
                execution_mode="conditional",  # Not supported in v1.0
                timeout_ms=60000,
            ),
            execution_graph=ModelExecutionGraph(
                nodes=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            coordination_rules=ModelCoordinationRules(
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        steps = [create_step(step_name="Conditional Step")]

        errors = await validate_workflow_definition(workflow_def, steps)

        # Should reject conditional mode
        assert len(errors) > 0, "Should reject conditional mode"
        assert any(
            "mode" in error.lower() or "conditional" in error.lower()
            for error in errors
        ), f"Error should mention execution mode: {errors}"

    @pytest.mark.asyncio
    async def test_streaming_execution_mode_rejected_in_v1(self) -> None:
        """Test that streaming execution mode is rejected in v1.0.

        STREAMING mode is not supported in v1.0 workflow execution.
        """
        workflow_def = ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="streaming_workflow",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Streaming workflow test",
                execution_mode="streaming",  # Not supported in v1.0
                timeout_ms=60000,
            ),
            execution_graph=ModelExecutionGraph(
                nodes=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            coordination_rules=ModelCoordinationRules(
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        steps = [create_step(step_name="Streaming Step")]

        errors = await validate_workflow_definition(workflow_def, steps)

        # Should reject streaming mode
        assert len(errors) > 0, "Should reject streaming mode"
        assert any(
            "mode" in error.lower() or "streaming" in error.lower() for error in errors
        ), f"Error should mention execution mode: {errors}"

    @pytest.mark.asyncio
    async def test_empty_workflow_rejected(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that empty workflow (no steps) is rejected."""
        errors = await validate_workflow_definition(base_workflow_definition, [])

        assert len(errors) > 0, "Should reject empty workflow"
        assert any("no steps" in error.lower() for error in errors), (
            f"Error should mention 'no steps': {errors}"
        )

    @pytest.mark.asyncio
    async def test_missing_step_name_detected(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that missing step name is detected.

        Note: ModelWorkflowStep requires step_name via Field(...), so this
        tests the validation layer catches improperly constructed steps.
        """
        # ModelWorkflowStep requires step_name, so we can't easily test this
        # through the normal path. The Pydantic validation will prevent creation.
        # This test verifies the invariant is enforced at model level.
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelWorkflowStep(
                step_name="",  # Empty name should fail min_length=1
                step_type="compute",
            )

    @pytest.mark.asyncio
    async def test_workflow_timeout_positive(self) -> None:
        """Test that workflow timeout must be positive."""
        # Pydantic validation enforces timeout_ms >= 1000
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelWorkflowDefinitionMetadata(
                workflow_name="invalid_timeout",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Invalid timeout test",
                execution_mode="sequential",
                timeout_ms=0,  # Invalid - must be >= 1000
            )


# ============================================================================
# Error Message Quality Tests
# ============================================================================


@pytest.mark.unit
class TestErrorMessageQuality:
    """Test that validation errors contain useful information."""

    @pytest.mark.asyncio
    async def test_missing_dependency_error_includes_step_name(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that missing dependency error includes the step name."""
        non_existent_id = uuid4()

        steps = [
            create_step(
                step_name="Orphan Step",
                depends_on=[non_existent_id],
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0
        # Error should include the step name for debugging
        assert any("Orphan Step" in error for error in errors), (
            f"Error should include step name: {errors}"
        )

    @pytest.mark.asyncio
    async def test_missing_dependency_error_includes_dependency_id(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that missing dependency error includes the missing dependency ID."""
        non_existent_id = uuid4()

        steps = [
            create_step(
                step_name="Test Step",
                depends_on=[non_existent_id],
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        assert len(errors) > 0
        # Error should include the missing dependency ID
        assert any(str(non_existent_id) in error for error in errors), (
            f"Error should include dependency ID: {errors}"
        )

    def test_cycle_error_uses_correct_error_code(self) -> None:
        """Test that cycle detection uses VALIDATION_ERROR code."""
        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            create_step(step_id=step_a_id, step_name="A", depends_on=[step_b_id]),
            create_step(step_id=step_b_id, step_name="B", depends_on=[step_a_id]),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            get_execution_order(steps)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases in workflow validation."""

    @pytest.mark.asyncio
    async def test_single_step_workflow_valid(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that single-step workflow is valid."""
        steps = [create_step(step_name="Only Step")]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Filter structural errors
        structural_errors = [
            e for e in errors if "step" in e.lower() and "no" not in e.lower()
        ]
        assert len(structural_errors) == 0, f"Single step should be valid: {errors}"

    @pytest.mark.slow
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_large_workflow_valid(
        self, parallel_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test validation performance with large workflow (100 steps)."""
        # Create a large linear dependency chain
        step_ids = [uuid4() for _ in range(100)]
        steps = []

        for i, step_id in enumerate(step_ids):
            depends_on = [step_ids[i - 1]] if i > 0 else []
            steps.append(
                create_step(
                    step_id=step_id,
                    step_name=f"Step {i}",
                    depends_on=depends_on,
                )
            )

        errors = await validate_workflow_definition(parallel_workflow_definition, steps)

        cycle_errors = [e for e in errors if "cycle" in e.lower()]
        assert len(cycle_errors) == 0, f"Large valid workflow should pass: {errors}"

    @pytest.mark.asyncio
    async def test_complex_dependency_graph_valid(
        self, parallel_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test validation with complex multi-path dependency graph."""
        #     A
        #    /|\
        #   B C D
        #   |X|/
        #   E F
        #    \|
        #     G
        step_a = uuid4()
        step_b = uuid4()
        step_c = uuid4()
        step_d = uuid4()
        step_e = uuid4()
        step_f = uuid4()
        step_g = uuid4()

        steps = [
            create_step(step_id=step_a, step_name="A", depends_on=[]),
            create_step(step_id=step_b, step_name="B", depends_on=[step_a]),
            create_step(step_id=step_c, step_name="C", depends_on=[step_a]),
            create_step(step_id=step_d, step_name="D", depends_on=[step_a]),
            create_step(step_id=step_e, step_name="E", depends_on=[step_b, step_c]),
            create_step(step_id=step_f, step_name="F", depends_on=[step_c, step_d]),
            create_step(step_id=step_g, step_name="G", depends_on=[step_e, step_f]),
        ]

        errors = await validate_workflow_definition(parallel_workflow_definition, steps)

        cycle_errors = [e for e in errors if "cycle" in e.lower()]
        assert len(cycle_errors) == 0, f"Complex valid graph should pass: {errors}"

    def test_execution_order_respects_priority(self) -> None:
        """Test that execution order respects step priority for independent steps.

        Note: Priority uses lower value = higher priority (executes first).
        This follows heap/queue semantics where priority=1 executes before priority=100.
        """
        # Two independent steps with different priorities
        step_high_priority = uuid4()
        step_low_priority = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_low_priority,
                step_name="Low Priority",
                step_type="compute",
                priority=100,  # Lower urgency (higher number = executes later)
                depends_on=[],
            ),
            ModelWorkflowStep(
                step_id=step_high_priority,
                step_name="High Priority",
                step_type="compute",
                priority=1,  # Higher urgency (lower number = executes first)
                depends_on=[],
            ),
        ]

        order = get_execution_order(steps)

        # Lower priority number should execute first (priority=1 before priority=100)
        high_idx = order.index(step_high_priority)
        low_idx = order.index(step_low_priority)
        assert high_idx < low_idx, "Lower priority number should execute first"

    @pytest.mark.asyncio
    async def test_disabled_steps_not_validated_for_cycles(
        self, base_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test behavior with disabled steps in dependency chain."""
        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            create_step(
                step_id=step_a_id,
                step_name="Step A",
                depends_on=[],
                enabled=True,
            ),
            create_step(
                step_id=step_b_id,
                step_name="Step B",
                depends_on=[step_a_id],
                enabled=False,  # Disabled step
            ),
        ]

        errors = await validate_workflow_definition(base_workflow_definition, steps)

        # Disabled steps are still part of validation (they exist in the graph)
        # but won't execute - so validation should still pass
        cycle_errors = [e for e in errors if "cycle" in e.lower()]
        assert len(cycle_errors) == 0, f"Should pass with disabled step: {errors}"
