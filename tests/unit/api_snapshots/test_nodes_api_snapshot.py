"""
Pre-refactor API snapshot tests for omnibase_core.nodes module.

These tests capture the public API surface before v0.4.0 refactoring.
If these tests fail due to intentional breaking changes, update them
in the same PR with a migration note in the changelog.

The nodes module provides the ONEX Four-Node Architecture:
- COMPUTE: Data processing and transformation
- EFFECT: External interactions (I/O)
- REDUCER: State aggregation and management
- ORCHESTRATOR: Workflow coordination

VERSION: 1.0.0 (API stability guarantee per nodes/__init__.py)
STABILITY: Node interfaces are frozen for code generation.
           Breaking changes require major version bump.
"""

import pytest

# Use explicit import path - omnibase_core.nodes is not exposed via omnibase_core.__all__
import omnibase_core.nodes as nodes  # noqa: PLR0402


class TestNodesAPISnapshot:
    """Snapshot tests for nodes module public API.

    These tests serve as a contract verification mechanism to ensure
    the public API surface remains stable across refactoring efforts.
    Any changes to __all__ exports will cause these tests to fail,
    alerting developers to potential breaking changes.
    """

    @pytest.mark.unit
    def test_nodes_all_defined(self) -> None:
        """Test that __all__ is defined in the nodes module.

        The __all__ attribute is required for explicit public API definition
        and controls what is exported via 'from omnibase_core.nodes import *'.
        """
        assert hasattr(nodes, "__all__"), "nodes module must define __all__"
        assert isinstance(nodes.__all__, list), "__all__ must be a list"
        assert len(nodes.__all__) > 0, "__all__ must not be empty"

    @pytest.mark.unit
    def test_nodes_exports_snapshot(self) -> None:
        """Verify public API exports match pre-refactor snapshot.

        This is the primary snapshot test - it captures the exact set of
        exports that existed before any refactoring. If this test fails,
        it means the public API has changed and requires review.

        Pre-refactor snapshot captured: 2025-12-03 (OMN-149)
        Total exports: 20 (4 nodes + 9 models + 7 enums)
        """
        # Pre-refactor API snapshot - captured from nodes/__init__.py
        expected_exports = {
            # Node implementations (4 nodes)
            "NodeCompute",
            "NodeEffect",
            "NodeOrchestrator",
            "NodeReducer",
            # Input/Output models (9 models)
            "ModelComputeInput",
            "ModelComputeOutput",
            "ModelEffectInput",
            "ModelEffectOutput",
            "ModelEffectTransaction",
            "ModelOrchestratorInput",
            "ModelOrchestratorOutput",
            "ModelReducerInput",
            "ModelReducerOutput",
            # Public enums - Orchestrator types (4 enums)
            "EnumActionType",
            "EnumBranchCondition",
            "EnumExecutionMode",
            "EnumWorkflowState",
            # Public enums - Reducer types (3 enums)
            "EnumConflictResolution",
            "EnumReductionType",
            "EnumStreamingMode",
        }

        actual_exports = set(nodes.__all__)

        # Check for missing exports (removals - breaking change)
        missing = expected_exports - actual_exports
        assert not missing, (
            f"BREAKING CHANGE: The following exports were removed from nodes module: "
            f"{sorted(missing)}. If intentional, update this snapshot and add migration notes."
        )

        # Check for new exports (additions - may be ok but should be reviewed)
        additions = actual_exports - expected_exports
        assert not additions, (
            f"New exports detected in nodes module: {sorted(additions)}. "
            f"If intentional, update this snapshot to include them."
        )

        # Exact match verification
        assert actual_exports == expected_exports, (
            f"nodes.__all__ does not match pre-refactor snapshot. "
            f"Expected: {sorted(expected_exports)}, Got: {sorted(actual_exports)}"
        )

    @pytest.mark.unit
    def test_nodes_exports_count(self) -> None:
        """Verify the expected number of exports.

        Pre-refactor count: 20 exports
        - 4 node classes: NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer
        - 9 model classes: 2 Compute + 2 Effect + 1 Transaction + 2 Orchestrator + 2 Reducer
        - 7 enum classes: 4 orchestrator + 3 reducer

        Breakdown:
        - Nodes (4): NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer
        - Models (9): ModelComputeInput, ModelComputeOutput, ModelEffectInput,
          ModelEffectOutput, ModelEffectTransaction, ModelOrchestratorInput,
          ModelOrchestratorOutput, ModelReducerInput, ModelReducerOutput
        - Enums (7): EnumActionType, EnumBranchCondition, EnumExecutionMode,
          EnumWorkflowState, EnumConflictResolution, EnumReductionType, EnumStreamingMode

        Total: 4 + 9 + 7 = 20 exports
        """
        expected_count = 20
        actual_count = len(nodes.__all__)
        assert actual_count == expected_count, (
            f"Export count changed from {expected_count} to {actual_count}. "
            f"Review changes and update snapshot if intentional."
        )

    @pytest.mark.unit
    def test_nodes_exports_accessible(self) -> None:
        """Verify all exports are actually accessible via getattr.

        This ensures that __all__ declarations match actual module attributes.
        A mismatch would indicate a broken export configuration.
        """
        for name in nodes.__all__:
            assert hasattr(nodes, name), (
                f"Export '{name}' declared in __all__ but not accessible. "
                f"Check import statements in nodes/__init__.py"
            )
            obj = getattr(nodes, name)
            assert obj is not None, f"Export '{name}' is None"

    @pytest.mark.unit
    def test_nodes_no_private_exports(self) -> None:
        """Verify no private modules or attributes are exposed in __all__.

        Private items (starting with _) should never be in the public API.
        """
        for name in nodes.__all__:
            assert not name.startswith("_"), (
                f"Private export '{name}' found in __all__. "
                f"Remove it from the public API."
            )


class TestNodesNodeClassesSnapshot:
    """Snapshot tests for node class exports.

    These tests verify the four core node types are exported correctly.
    """

    @pytest.mark.unit
    def test_node_classes_snapshot(self) -> None:
        """Verify all node classes are exported."""
        expected_node_classes = {
            "NodeCompute",
            "NodeEffect",
            "NodeOrchestrator",
            "NodeReducer",
        }

        actual_exports = set(nodes.__all__)
        node_classes_in_exports = expected_node_classes & actual_exports

        assert (
            node_classes_in_exports == expected_node_classes
        ), f"Missing node classes: {expected_node_classes - node_classes_in_exports}"

    @pytest.mark.unit
    def test_node_classes_are_types(self) -> None:
        """Verify node exports are actual class types."""
        node_names = ["NodeCompute", "NodeEffect", "NodeOrchestrator", "NodeReducer"]

        for name in node_names:
            obj = getattr(nodes, name)
            assert isinstance(obj, type), f"{name} should be a class, got {type(obj)}"

    @pytest.mark.unit
    def test_node_classes_importable_directly(self) -> None:
        """Verify node classes can be imported directly from nodes module."""
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        assert NodeCompute is not None
        assert NodeEffect is not None
        assert NodeOrchestrator is not None
        assert NodeReducer is not None


class TestNodesModelExportsSnapshot:
    """Snapshot tests for model exports.

    These tests verify input/output models for all node types.
    """

    @pytest.mark.unit
    def test_model_classes_snapshot(self) -> None:
        """Verify all model classes are exported."""
        expected_models = {
            # Compute models
            "ModelComputeInput",
            "ModelComputeOutput",
            # Effect models
            "ModelEffectInput",
            "ModelEffectOutput",
            "ModelEffectTransaction",
            # Orchestrator models
            "ModelOrchestratorInput",
            "ModelOrchestratorOutput",
            # Reducer models
            "ModelReducerInput",
            "ModelReducerOutput",
        }

        actual_exports = set(nodes.__all__)
        models_in_exports = expected_models & actual_exports

        assert (
            models_in_exports == expected_models
        ), f"Missing models: {expected_models - models_in_exports}"

    @pytest.mark.unit
    def test_model_classes_are_types(self) -> None:
        """Verify model exports are actual class types."""
        model_names = [
            "ModelComputeInput",
            "ModelComputeOutput",
            "ModelEffectInput",
            "ModelEffectOutput",
            "ModelEffectTransaction",
            "ModelOrchestratorInput",
            "ModelOrchestratorOutput",
            "ModelReducerInput",
            "ModelReducerOutput",
        ]

        for name in model_names:
            obj = getattr(nodes, name)
            assert isinstance(obj, type), f"{name} should be a class, got {type(obj)}"

    @pytest.mark.unit
    def test_model_classes_importable_directly(self) -> None:
        """Verify model classes can be imported directly from nodes module."""
        from omnibase_core.nodes import (
            ModelComputeInput,
            ModelComputeOutput,
            ModelEffectInput,
            ModelEffectOutput,
            ModelEffectTransaction,
            ModelOrchestratorInput,
            ModelOrchestratorOutput,
            ModelReducerInput,
            ModelReducerOutput,
        )

        assert ModelComputeInput is not None
        assert ModelComputeOutput is not None
        assert ModelEffectInput is not None
        assert ModelEffectOutput is not None
        assert ModelEffectTransaction is not None
        assert ModelOrchestratorInput is not None
        assert ModelOrchestratorOutput is not None
        assert ModelReducerInput is not None
        assert ModelReducerOutput is not None


class TestNodesEnumExportsSnapshot:
    """Snapshot tests for enum exports.

    These tests verify orchestrator and reducer enums are exported.
    """

    @pytest.mark.unit
    def test_enum_classes_snapshot(self) -> None:
        """Verify all enum classes are exported."""
        expected_enums = {
            # Orchestrator enums
            "EnumActionType",
            "EnumBranchCondition",
            "EnumExecutionMode",
            "EnumWorkflowState",
            # Reducer enums
            "EnumConflictResolution",
            "EnumReductionType",
            "EnumStreamingMode",
        }

        actual_exports = set(nodes.__all__)
        enums_in_exports = expected_enums & actual_exports

        assert (
            enums_in_exports == expected_enums
        ), f"Missing enums: {expected_enums - enums_in_exports}"

    @pytest.mark.unit
    def test_enum_classes_are_enum_types(self) -> None:
        """Verify enum exports have __members__ attribute (enum behavior)."""
        enum_names = [
            "EnumActionType",
            "EnumBranchCondition",
            "EnumExecutionMode",
            "EnumWorkflowState",
            "EnumConflictResolution",
            "EnumReductionType",
            "EnumStreamingMode",
        ]

        for name in enum_names:
            obj = getattr(nodes, name)
            assert hasattr(
                obj, "__members__"
            ), f"{name} should be an enum (have __members__), got {type(obj)}"

    @pytest.mark.unit
    def test_enum_classes_importable_directly(self) -> None:
        """Verify enum classes can be imported directly from nodes module."""
        from omnibase_core.nodes import (
            EnumActionType,
            EnumBranchCondition,
            EnumConflictResolution,
            EnumExecutionMode,
            EnumReductionType,
            EnumStreamingMode,
            EnumWorkflowState,
        )

        assert EnumActionType is not None
        assert EnumBranchCondition is not None
        assert EnumExecutionMode is not None
        assert EnumWorkflowState is not None
        assert EnumConflictResolution is not None
        assert EnumReductionType is not None
        assert EnumStreamingMode is not None


class TestNodesInternalNotExposed:
    """Tests to verify internal implementation details are NOT exposed.

    The nodes/__init__.py explicitly notes that certain models are
    internal and should NOT be exported.
    """

    @pytest.mark.unit
    def test_internal_models_not_exported(self) -> None:
        """Verify internal models are NOT in __all__.

        Per nodes/__init__.py comment, these are internal:
        - ModelConflictResolver
        - ModelDependencyGraph
        - ModelLoadBalancer
        - ModelStreamingWindow
        - ModelAction
        - ModelWorkflowStep
        """
        internal_models = {
            "ModelConflictResolver",
            "ModelDependencyGraph",
            "ModelLoadBalancer",
            "ModelStreamingWindow",
            "ModelAction",
            "ModelWorkflowStep",
        }

        actual_exports = set(nodes.__all__)
        leaked_internals = internal_models & actual_exports

        assert not leaked_internals, (
            f"Internal models leaked to public API: {leaked_internals}. "
            f"These should remain internal implementation details."
        )


class TestNodesModuleDocumentation:
    """Tests for module documentation presence."""

    @pytest.mark.unit
    def test_nodes_has_docstring(self) -> None:
        """Test that nodes module has a docstring."""
        assert nodes.__doc__ is not None, "nodes module must have a docstring"
        assert len(nodes.__doc__) > 0, "nodes module docstring must not be empty"

    @pytest.mark.unit
    def test_nodes_docstring_mentions_version(self) -> None:
        """Test that docstring includes version information."""
        docstring = nodes.__doc__ or ""
        assert (
            "VERSION" in docstring or "1.0.0" in docstring
        ), "nodes module docstring should mention version for stability guarantee"

    @pytest.mark.unit
    def test_nodes_docstring_mentions_stability(self) -> None:
        """Test that docstring includes stability guarantee."""
        docstring = nodes.__doc__ or ""
        assert (
            "STABILITY" in docstring or "frozen" in docstring.lower()
        ), "nodes module docstring should mention stability guarantee"
