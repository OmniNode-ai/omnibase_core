"""
Tests for ModelDependencyGraph - comprehensive coverage.

Tests dependency graph construction, topological ordering, cycle detection,
and dependency resolution for workflow step coordination.

ZERO TOLERANCE: No Any types allowed.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_workflow_execution import (
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.models.orchestrator.model_action import ModelThunk
from omnibase_core.models.workflows.model_dependency_graph import ModelDependencyGraph
from omnibase_core.models.workflows.model_workflow_step_execution import (
    ModelWorkflowStepExecution,
)


class TestDependencyGraphCreation:
    """Test dependency graph initialization and basic setup."""

    def test_empty_graph_creation(self) -> None:
        """Test creating an empty dependency graph."""
        graph = ModelDependencyGraph()

        assert graph.nodes == {}
        assert graph.edges == {}
        assert graph.in_degree == {}

    def test_graph_with_default_factory_fields(self) -> None:
        """Test that default factories create empty collections."""
        graph = ModelDependencyGraph()

        # All collections should be empty dicts
        assert isinstance(graph.nodes, dict)
        assert isinstance(graph.edges, dict)
        assert isinstance(graph.in_degree, dict)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert len(graph.in_degree) == 0


class TestAddingSteps:
    """Test adding workflow steps to the dependency graph."""

    def test_add_single_step(self) -> None:
        """Test adding a single workflow step to the graph."""
        graph = ModelDependencyGraph()
        step = ModelWorkflowStepExecution(
            step_name="test_step",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step)

        step_id_str = str(step.step_id)
        assert step_id_str in graph.nodes
        assert graph.nodes[step_id_str] == step
        assert step_id_str in graph.edges
        assert graph.edges[step_id_str] == []
        assert step_id_str in graph.in_degree
        assert graph.in_degree[step_id_str] == 0

    def test_add_multiple_steps(self) -> None:
        """Test adding multiple independent workflow steps."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{i}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
            for i in range(5)
        ]

        for step in steps:
            graph.add_step(step)

        assert len(graph.nodes) == 5
        assert len(graph.edges) == 5
        assert len(graph.in_degree) == 5

        # All steps should have zero in-degree (independent)
        for step in steps:
            step_id_str = str(step.step_id)
            assert graph.in_degree[step_id_str] == 0

    def test_add_step_twice_updates_existing(self) -> None:
        """Test adding the same step twice updates the existing entry."""
        graph = ModelDependencyGraph()
        step = ModelWorkflowStepExecution(
            step_name="test_step",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step)
        original_count = len(graph.nodes)

        # Add again - should not duplicate
        graph.add_step(step)

        assert len(graph.nodes) == original_count
        step_id_str = str(step.step_id)
        assert graph.nodes[step_id_str] == step

    def test_add_step_with_different_execution_modes(self) -> None:
        """Test adding steps with various execution modes."""
        graph = ModelDependencyGraph()
        modes = [
            EnumExecutionMode.SEQUENTIAL,
            EnumExecutionMode.PARALLEL,
            EnumExecutionMode.BATCH,
        ]

        for i, mode in enumerate(modes):
            step = ModelWorkflowStepExecution(
                step_name=f"step_{i}",
                execution_mode=mode,
            )
            graph.add_step(step)

        assert len(graph.nodes) == len(modes)


class TestAddingDependencies:
    """Test adding dependencies between workflow steps."""

    def test_add_simple_dependency(self) -> None:
        """Test adding a simple A -> B dependency."""
        graph = ModelDependencyGraph()
        step_a = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        step_b = ModelWorkflowStepExecution(
            step_name="step_b",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step_a)
        graph.add_step(step_b)

        step_a_id = str(step_a.step_id)
        step_b_id = str(step_b.step_id)

        # B depends on A
        graph.add_dependency(step_a_id, step_b_id)

        assert step_b_id in graph.edges[step_a_id]
        assert graph.in_degree[step_b_id] == 1
        assert graph.in_degree[step_a_id] == 0

    def test_add_chain_dependencies(self) -> None:
        """Test adding chain dependencies: A -> B -> C -> D."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{chr(65 + i)}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
            for i in range(4)
        ]

        for step in steps:
            graph.add_step(step)

        # Create chain: A -> B -> C -> D
        for i in range(len(steps) - 1):
            from_id = str(steps[i].step_id)
            to_id = str(steps[i + 1].step_id)
            graph.add_dependency(from_id, to_id)

        # First step has no dependencies
        assert graph.in_degree[str(steps[0].step_id)] == 0
        # Middle steps have 1 dependency each
        assert graph.in_degree[str(steps[1].step_id)] == 1
        assert graph.in_degree[str(steps[2].step_id)] == 1
        # Last step has 1 dependency
        assert graph.in_degree[str(steps[3].step_id)] == 1

    def test_add_diamond_dependencies(self) -> None:
        """Test adding diamond dependencies: A -> B,C -> D."""
        graph = ModelDependencyGraph()
        steps = {
            "A": ModelWorkflowStepExecution(
                step_name="step_A",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
            "B": ModelWorkflowStepExecution(
                step_name="step_B",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "C": ModelWorkflowStepExecution(
                step_name="step_C",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "D": ModelWorkflowStepExecution(
                step_name="step_D",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
        }

        for step in steps.values():
            graph.add_step(step)

        # Create diamond: A -> B, A -> C, B -> D, C -> D
        a_id = str(steps["A"].step_id)
        b_id = str(steps["B"].step_id)
        c_id = str(steps["C"].step_id)
        d_id = str(steps["D"].step_id)

        graph.add_dependency(a_id, b_id)
        graph.add_dependency(a_id, c_id)
        graph.add_dependency(b_id, d_id)
        graph.add_dependency(c_id, d_id)

        # A has no dependencies
        assert graph.in_degree[a_id] == 0
        # B and C each depend on A
        assert graph.in_degree[b_id] == 1
        assert graph.in_degree[c_id] == 1
        # D depends on both B and C
        assert graph.in_degree[d_id] == 2

    def test_add_dependency_creates_edges_entry(self) -> None:
        """Test that adding dependency to non-existing node creates edges entry."""
        graph = ModelDependencyGraph()
        step_a_id = "step_a"
        step_b_id = "step_b"

        graph.add_dependency(step_a_id, step_b_id)

        assert step_a_id in graph.edges
        assert step_b_id in graph.edges[step_a_id]

    def test_add_multiple_dependencies_from_one_step(self) -> None:
        """Test adding multiple outgoing dependencies from one step."""
        graph = ModelDependencyGraph()
        root = ModelWorkflowStepExecution(
            step_name="root",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        dependents = [
            ModelWorkflowStepExecution(
                step_name=f"dependent_{i}",
                execution_mode=EnumExecutionMode.PARALLEL,
            )
            for i in range(3)
        ]

        graph.add_step(root)
        for dep in dependents:
            graph.add_step(dep)

        root_id = str(root.step_id)
        for dep in dependents:
            graph.add_dependency(root_id, str(dep.step_id))

        assert len(graph.edges[root_id]) == 3
        assert graph.in_degree[root_id] == 0
        for dep in dependents:
            assert graph.in_degree[str(dep.step_id)] == 1


class TestGetReadySteps:
    """Test identifying steps that are ready to execute."""

    def test_get_ready_steps_empty_graph(self) -> None:
        """Test getting ready steps from empty graph."""
        graph = ModelDependencyGraph()

        ready = graph.get_ready_steps()

        assert ready == []

    def test_get_ready_steps_all_independent(self) -> None:
        """Test getting ready steps when all steps are independent."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{i}",
                execution_mode=EnumExecutionMode.PARALLEL,
            )
            for i in range(3)
        ]

        for step in steps:
            graph.add_step(step)

        ready = graph.get_ready_steps()

        # All steps should be ready
        assert len(ready) == 3
        for step in steps:
            assert str(step.step_id) in ready

    def test_get_ready_steps_with_dependencies(self) -> None:
        """Test getting ready steps with dependency chain."""
        graph = ModelDependencyGraph()
        step_a = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        step_b = ModelWorkflowStepExecution(
            step_name="step_b",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step_a)
        graph.add_step(step_b)
        graph.add_dependency(str(step_a.step_id), str(step_b.step_id))

        ready = graph.get_ready_steps()

        # Only step_a should be ready
        assert len(ready) == 1
        assert str(step_a.step_id) in ready
        assert str(step_b.step_id) not in ready

    def test_get_ready_steps_excludes_completed(self) -> None:
        """Test that completed steps are not in ready list."""
        graph = ModelDependencyGraph()
        step = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step)
        step.state = EnumWorkflowState.COMPLETED

        ready = graph.get_ready_steps()

        # Completed step should not be ready
        assert str(step.step_id) not in ready

    def test_get_ready_steps_excludes_running(self) -> None:
        """Test that running steps are not in ready list."""
        graph = ModelDependencyGraph()
        step = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step)
        step.state = EnumWorkflowState.RUNNING

        ready = graph.get_ready_steps()

        assert str(step.step_id) not in ready

    def test_get_ready_steps_diamond_pattern(self) -> None:
        """Test ready steps in diamond dependency pattern."""
        graph = ModelDependencyGraph()
        steps = {
            "A": ModelWorkflowStepExecution(
                step_name="step_A",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
            "B": ModelWorkflowStepExecution(
                step_name="step_B",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "C": ModelWorkflowStepExecution(
                step_name="step_C",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "D": ModelWorkflowStepExecution(
                step_name="step_D",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
        }

        for step in steps.values():
            graph.add_step(step)

        a_id = str(steps["A"].step_id)
        b_id = str(steps["B"].step_id)
        c_id = str(steps["C"].step_id)
        d_id = str(steps["D"].step_id)

        graph.add_dependency(a_id, b_id)
        graph.add_dependency(a_id, c_id)
        graph.add_dependency(b_id, d_id)
        graph.add_dependency(c_id, d_id)

        # Initially only A is ready
        ready = graph.get_ready_steps()
        assert len(ready) == 1
        assert a_id in ready


class TestMarkCompleted:
    """Test marking steps as completed and updating dependencies."""

    def test_mark_completed_single_step(self) -> None:
        """Test marking a single step as completed."""
        graph = ModelDependencyGraph()
        step = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step)
        graph.mark_completed(step.step_id)

        assert graph.nodes[str(step.step_id)].state == EnumWorkflowState.COMPLETED

    def test_mark_completed_updates_dependent_in_degree(self) -> None:
        """Test that marking step completed decreases dependent's in-degree."""
        graph = ModelDependencyGraph()
        step_a = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        step_b = ModelWorkflowStepExecution(
            step_name="step_b",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step_a)
        graph.add_step(step_b)
        graph.add_dependency(str(step_a.step_id), str(step_b.step_id))

        # B should have in-degree of 1
        assert graph.in_degree[str(step_b.step_id)] == 1

        # Complete A
        graph.mark_completed(step_a.step_id)

        # B's in-degree should now be 0
        assert graph.in_degree[str(step_b.step_id)] == 0

    def test_mark_completed_chain_execution(self) -> None:
        """Test sequential completion of dependency chain."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{i}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
            for i in range(3)
        ]

        for step in steps:
            graph.add_step(step)

        # Chain: 0 -> 1 -> 2
        graph.add_dependency(str(steps[0].step_id), str(steps[1].step_id))
        graph.add_dependency(str(steps[1].step_id), str(steps[2].step_id))

        # Initially only step 0 is ready
        ready = graph.get_ready_steps()
        assert len(ready) == 1
        assert str(steps[0].step_id) in ready

        # Complete step 0
        graph.mark_completed(steps[0].step_id)

        # Now step 1 should be ready
        ready = graph.get_ready_steps()
        assert len(ready) == 1
        assert str(steps[1].step_id) in ready

        # Complete step 1
        graph.mark_completed(steps[1].step_id)

        # Now step 2 should be ready
        ready = graph.get_ready_steps()
        assert len(ready) == 1
        assert str(steps[2].step_id) in ready

    def test_mark_completed_non_existent_step(self) -> None:
        """Test marking non-existent step as completed (graceful handling)."""
        graph = ModelDependencyGraph()
        non_existent_id = uuid4()

        # Should not raise an error
        graph.mark_completed(non_existent_id)

    def test_mark_completed_diamond_pattern(self) -> None:
        """Test completion flow in diamond pattern."""
        graph = ModelDependencyGraph()
        steps = {
            "A": ModelWorkflowStepExecution(
                step_name="step_A",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
            "B": ModelWorkflowStepExecution(
                step_name="step_B",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "C": ModelWorkflowStepExecution(
                step_name="step_C",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "D": ModelWorkflowStepExecution(
                step_name="step_D",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
        }

        for step in steps.values():
            graph.add_step(step)

        a_id = str(steps["A"].step_id)
        b_id = str(steps["B"].step_id)
        c_id = str(steps["C"].step_id)
        d_id = str(steps["D"].step_id)

        graph.add_dependency(a_id, b_id)
        graph.add_dependency(a_id, c_id)
        graph.add_dependency(b_id, d_id)
        graph.add_dependency(c_id, d_id)

        # D should have in-degree 2
        assert graph.in_degree[d_id] == 2

        # Complete A
        graph.mark_completed(steps["A"].step_id)

        # B and C should now be ready
        ready = graph.get_ready_steps()
        assert len(ready) == 2
        assert b_id in ready
        assert c_id in ready

        # Complete B
        graph.mark_completed(steps["B"].step_id)

        # D still has in-degree 1 (waiting for C)
        assert graph.in_degree[d_id] == 1

        # Complete C
        graph.mark_completed(steps["C"].step_id)

        # Now D should be ready
        assert graph.in_degree[d_id] == 0
        ready = graph.get_ready_steps()
        assert len(ready) == 1
        assert d_id in ready


class TestCycleDetection:
    """Test cycle detection in dependency graphs."""

    def test_has_cycles_empty_graph(self) -> None:
        """Test cycle detection on empty graph."""
        graph = ModelDependencyGraph()

        assert not graph.has_cycles()

    def test_has_cycles_single_step(self) -> None:
        """Test cycle detection with single independent step."""
        graph = ModelDependencyGraph()
        step = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step)

        assert not graph.has_cycles()

    def test_has_cycles_simple_chain(self) -> None:
        """Test cycle detection on simple chain (no cycles)."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{i}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
            for i in range(3)
        ]

        for step in steps:
            graph.add_step(step)

        graph.add_dependency(str(steps[0].step_id), str(steps[1].step_id))
        graph.add_dependency(str(steps[1].step_id), str(steps[2].step_id))

        assert not graph.has_cycles()

    def test_has_cycles_self_loop(self) -> None:
        """Test cycle detection with self-loop."""
        graph = ModelDependencyGraph()
        step = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step)
        step_id = str(step.step_id)
        graph.add_dependency(step_id, step_id)

        assert graph.has_cycles()

    def test_has_cycles_simple_cycle(self) -> None:
        """Test cycle detection with simple A -> B -> A cycle."""
        graph = ModelDependencyGraph()
        step_a = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        step_b = ModelWorkflowStepExecution(
            step_name="step_b",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step_a)
        graph.add_step(step_b)

        a_id = str(step_a.step_id)
        b_id = str(step_b.step_id)

        graph.add_dependency(a_id, b_id)
        graph.add_dependency(b_id, a_id)

        assert graph.has_cycles()

    def test_has_cycles_three_node_cycle(self) -> None:
        """Test cycle detection with A -> B -> C -> A cycle."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{chr(65 + i)}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
            for i in range(3)
        ]

        for step in steps:
            graph.add_step(step)

        a_id = str(steps[0].step_id)
        b_id = str(steps[1].step_id)
        c_id = str(steps[2].step_id)

        graph.add_dependency(a_id, b_id)
        graph.add_dependency(b_id, c_id)
        graph.add_dependency(c_id, a_id)

        assert graph.has_cycles()

    def test_has_cycles_diamond_no_cycle(self) -> None:
        """Test cycle detection on diamond pattern (no cycles)."""
        graph = ModelDependencyGraph()
        steps = {
            "A": ModelWorkflowStepExecution(
                step_name="step_A",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
            "B": ModelWorkflowStepExecution(
                step_name="step_B",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "C": ModelWorkflowStepExecution(
                step_name="step_C",
                execution_mode=EnumExecutionMode.PARALLEL,
            ),
            "D": ModelWorkflowStepExecution(
                step_name="step_D",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            ),
        }

        for step in steps.values():
            graph.add_step(step)

        a_id = str(steps["A"].step_id)
        b_id = str(steps["B"].step_id)
        c_id = str(steps["C"].step_id)
        d_id = str(steps["D"].step_id)

        graph.add_dependency(a_id, b_id)
        graph.add_dependency(a_id, c_id)
        graph.add_dependency(b_id, d_id)
        graph.add_dependency(c_id, d_id)

        assert not graph.has_cycles()

    def test_has_cycles_complex_graph_with_cycle(self) -> None:
        """Test cycle detection in complex graph with hidden cycle."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{i}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
            for i in range(5)
        ]

        for step in steps:
            graph.add_step(step)

        ids = [str(step.step_id) for step in steps]

        # Create complex dependencies with cycle
        graph.add_dependency(ids[0], ids[1])
        graph.add_dependency(ids[1], ids[2])
        graph.add_dependency(ids[2], ids[3])
        graph.add_dependency(ids[3], ids[4])
        graph.add_dependency(ids[4], ids[1])  # Cycle back to node 1

        assert graph.has_cycles()


class TestModelConfiguration:
    """Test Pydantic model configuration."""

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored."""
        graph = ModelDependencyGraph(
            nodes={},
            edges={},
            in_degree={},
            extra_field="ignored",  # type: ignore[call-arg]
        )

        assert not hasattr(graph, "extra_field")

    def test_arbitrary_types_allowed(self) -> None:
        """Test that arbitrary types (ModelWorkflowStepExecution) are allowed."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph = ModelDependencyGraph(
            nodes={str(step.step_id): step},
            edges={},
            in_degree={},
        )

        assert graph.nodes[str(step.step_id)] == step

    def test_validate_assignment(self) -> None:
        """Test that assignment validation is enabled."""
        graph = ModelDependencyGraph()

        # Should allow valid assignment
        graph.nodes = {}
        graph.edges = {}
        graph.in_degree = {}


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_graph_performance(self) -> None:
        """Test handling large graph with many steps."""
        graph = ModelDependencyGraph()
        steps = [
            ModelWorkflowStepExecution(
                step_name=f"step_{i}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
            for i in range(100)
        ]

        for step in steps:
            graph.add_step(step)

        assert len(graph.nodes) == 100

    def test_multiple_dependencies_same_target(self) -> None:
        """Test multiple steps depending on same target."""
        graph = ModelDependencyGraph()
        root = ModelWorkflowStepExecution(
            step_name="root",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        targets = [
            ModelWorkflowStepExecution(
                step_name=f"target_{i}",
                execution_mode=EnumExecutionMode.PARALLEL,
            )
            for i in range(3)
        ]

        graph.add_step(root)
        for target in targets:
            graph.add_step(target)

        root_id = str(root.step_id)
        for target in targets:
            target_id = str(target.step_id)
            # All targets depend on root
            for other in targets:
                if other != target:
                    graph.add_dependency(str(other.step_id), target_id)

        # Each target should have in-degree of 2
        for target in targets:
            assert graph.in_degree[str(target.step_id)] == 2

    def test_zero_in_degree_after_all_dependencies_met(self) -> None:
        """Test that in-degree reaches zero after all dependencies completed."""
        graph = ModelDependencyGraph()
        deps = [
            ModelWorkflowStepExecution(
                step_name=f"dep_{i}",
                execution_mode=EnumExecutionMode.PARALLEL,
            )
            for i in range(3)
        ]
        target = ModelWorkflowStepExecution(
            step_name="target",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        for dep in deps:
            graph.add_step(dep)
        graph.add_step(target)

        target_id = str(target.step_id)
        for dep in deps:
            graph.add_dependency(str(dep.step_id), target_id)

        # Target should have in-degree 3
        assert graph.in_degree[target_id] == 3

        # Complete all dependencies
        for dep in deps:
            graph.mark_completed(dep.step_id)

        # Target should now have in-degree 0
        assert graph.in_degree[target_id] == 0

    def test_mark_completed_with_missing_dependent_in_degree(self) -> None:
        """Test mark_completed when dependent step not in in_degree dict."""
        graph = ModelDependencyGraph()
        step_a = ModelWorkflowStepExecution(
            step_name="step_a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        graph.add_step(step_a)
        step_a_id = str(step_a.step_id)

        # Manually add edge to non-existent step (bypassing add_step/add_dependency)
        # This creates the edge case where dependent_step is not in in_degree
        graph.edges[step_a_id] = ["non_existent_step"]

        # Mark step_a as completed - should not raise error even though
        # "non_existent_step" is not in in_degree dictionary
        graph.mark_completed(step_a.step_id)

        # Verify step_a was marked completed
        assert graph.nodes[step_a_id].state == EnumWorkflowState.COMPLETED


__all__ = [
    "TestDependencyGraphCreation",
    "TestAddingSteps",
    "TestAddingDependencies",
    "TestGetReadySteps",
    "TestMarkCompleted",
    "TestCycleDetection",
    "TestModelConfiguration",
    "TestEdgeCases",
]
