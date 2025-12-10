"""Pre-refactor import path verification tests.

These tests verify that all documented import paths work correctly.
This ensures backwards compatibility for users importing from specific paths.

Part of : Create pre-refactor API snapshot tests.

The import paths tested here represent the public API contract that must
be maintained across refactors to avoid breaking user code.
"""

import pytest


@pytest.mark.unit
class TestNodesModuleImports:
    """Verify documented import paths from omnibase_core.nodes work correctly."""

    def test_nodes_core_classes_import(self) -> None:
        """Verify core node classes are importable from nodes module."""
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        # Verify they are classes (types)
        assert isinstance(NodeCompute, type), "NodeCompute should be a class"
        assert isinstance(NodeEffect, type), "NodeEffect should be a class"
        assert isinstance(NodeReducer, type), "NodeReducer should be a class"
        assert isinstance(NodeOrchestrator, type), "NodeOrchestrator should be a class"

    def test_nodes_core_classes_have_process_method(self) -> None:
        """Verify core node classes have the expected process method."""
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        # All nodes should have a process method
        assert hasattr(NodeCompute, "process"), "NodeCompute should have process method"
        assert hasattr(NodeEffect, "process"), "NodeEffect should have process method"
        assert hasattr(NodeReducer, "process"), "NodeReducer should have process method"
        assert hasattr(NodeOrchestrator, "process"), (
            "NodeOrchestrator should have process method"
        )

    def test_nodes_compute_io_models_import(self) -> None:
        """Verify COMPUTE node I/O models are importable."""
        from omnibase_core.nodes import ModelComputeInput, ModelComputeOutput

        # Should be types (Pydantic models)
        assert isinstance(ModelComputeInput, type), "ModelComputeInput should be a type"
        assert isinstance(ModelComputeOutput, type), (
            "ModelComputeOutput should be a type"
        )

    def test_nodes_effect_io_models_import(self) -> None:
        """Verify EFFECT node I/O models are importable."""
        from omnibase_core.nodes import ModelEffectInput, ModelEffectOutput

        # Should be types (Pydantic models)
        assert isinstance(ModelEffectInput, type), "ModelEffectInput should be a type"
        assert isinstance(ModelEffectOutput, type), "ModelEffectOutput should be a type"

    def test_nodes_reducer_io_models_import(self) -> None:
        """Verify REDUCER node I/O models are importable."""
        from omnibase_core.nodes import ModelReducerInput, ModelReducerOutput

        # Should be types (Pydantic models)
        assert isinstance(ModelReducerInput, type), "ModelReducerInput should be a type"
        assert isinstance(ModelReducerOutput, type), (
            "ModelReducerOutput should be a type"
        )

    def test_nodes_orchestrator_io_models_import(self) -> None:
        """Verify ORCHESTRATOR node I/O models are importable."""
        from omnibase_core.nodes import ModelOrchestratorInput, ModelOrchestratorOutput

        # Should be types (Pydantic models)
        assert isinstance(ModelOrchestratorInput, type), (
            "ModelOrchestratorInput should be a type"
        )
        assert isinstance(ModelOrchestratorOutput, type), (
            "ModelOrchestratorOutput should be a type"
        )

    def test_nodes_effect_transaction_model_import(self) -> None:
        """Verify ModelEffectTransaction is importable from nodes for type hints."""
        from omnibase_core.nodes import ModelEffectTransaction

        # Should be a type (for rollback failure callback type hints)
        assert isinstance(ModelEffectTransaction, type), (
            "ModelEffectTransaction should be a type"
        )

    def test_nodes_all_io_models_combined_import(self) -> None:
        """Verify all I/O models can be imported together without conflicts."""
        from omnibase_core.nodes import (
            ModelComputeInput,
            ModelComputeOutput,
            ModelEffectInput,
            ModelEffectOutput,
            ModelOrchestratorInput,
            ModelOrchestratorOutput,
            ModelReducerInput,
            ModelReducerOutput,
        )

        # All should be distinct types
        types_list = [
            ModelComputeInput,
            ModelComputeOutput,
            ModelEffectInput,
            ModelEffectOutput,
            ModelReducerInput,
            ModelReducerOutput,
            ModelOrchestratorInput,
            ModelOrchestratorOutput,
        ]

        for t in types_list:
            assert isinstance(t, type), f"{t.__name__} should be a type"

    def test_nodes_enums_import(self) -> None:
        """Verify public enums are importable from nodes module."""
        # All should be enum types
        from enum import EnumMeta

        from omnibase_core.nodes import (
            EnumActionType,
            EnumBranchCondition,
            EnumConflictResolution,
            EnumExecutionMode,
            EnumReductionType,
            EnumStreamingMode,
            EnumWorkflowState,
        )

        assert isinstance(EnumActionType, EnumMeta), (
            "EnumActionType should be an enum type"
        )
        assert isinstance(EnumBranchCondition, EnumMeta), (
            "EnumBranchCondition should be an enum type"
        )
        assert isinstance(EnumExecutionMode, EnumMeta), (
            "EnumExecutionMode should be an enum type"
        )
        assert isinstance(EnumWorkflowState, EnumMeta), (
            "EnumWorkflowState should be an enum type"
        )
        assert isinstance(EnumConflictResolution, EnumMeta), (
            "EnumConflictResolution should be an enum type"
        )
        assert isinstance(EnumReductionType, EnumMeta), (
            "EnumReductionType should be an enum type"
        )
        assert isinstance(EnumStreamingMode, EnumMeta), (
            "EnumStreamingMode should be an enum type"
        )


@pytest.mark.unit
class TestNodesDeclarativeImports:
    """Verify declarative node class imports.

    NOTE: NodeReducer and NodeOrchestrator are the primary declarative node classes.
    They are exported from omnibase_core.nodes.__init__.py.

    These tests verify the classes are properly exported and importable.
    """

    def test_declarative_classes_exist_and_exported(self) -> None:
        """Verify declarative classes exist and are exported from nodes module.

        This test verifies the classes exist at their source locations
        and are part of the public API.
        """
        # These classes should be exported from nodes.__init__.py
        from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
        from omnibase_core.nodes.node_reducer import NodeReducer

        assert isinstance(NodeReducer, type)
        assert isinstance(NodeOrchestrator, type)

    def test_nodes_reducer_import(self) -> None:
        """Verify NodeReducer is importable from nodes module."""
        from omnibase_core.nodes import NodeReducer

        assert isinstance(NodeReducer, type)

    def test_nodes_orchestrator_import(self) -> None:
        """Verify NodeOrchestrator is importable from nodes module."""
        from omnibase_core.nodes import NodeOrchestrator

        assert isinstance(NodeOrchestrator, type)


@pytest.mark.unit
class TestInfrastructureModuleImports:
    """Verify documented import paths from omnibase_core.infrastructure work correctly."""

    def test_infrastructure_base_classes_import(self) -> None:
        """Verify infrastructure base classes are importable."""
        from omnibase_core.infrastructure import NodeBase, NodeCoreBase

        assert isinstance(NodeCoreBase, type), "NodeCoreBase should be a class"
        assert isinstance(NodeBase, type), "NodeBase should be a class"

    def test_infrastructure_base_classes_are_independent(self) -> None:
        """Verify base classes are independent (sibling classes).

        NOTE: NodeCoreBase inherits from ABC and is the recommended base for
        the 4-node architecture (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR).
        NodeBase inherits from WorkflowReducerInterface and provides LlamaIndex
        workflow integration with observable state transitions.

        They are independent classes serving different purposes - neither
        inherits from the other.
        """
        from abc import ABC

        from omnibase_core.infrastructure import NodeBase, NodeCoreBase

        # NodeCoreBase is an abstract base class
        assert issubclass(NodeCoreBase, ABC), "NodeCoreBase should be an ABC"

        # They are sibling classes (neither inherits from the other)
        assert not issubclass(NodeCoreBase, NodeBase), (
            "NodeCoreBase should not inherit from NodeBase"
        )
        assert not issubclass(NodeBase, NodeCoreBase), (
            "NodeBase should not inherit from NodeCoreBase"
        )

    def test_infrastructure_circuit_breaker_import(self) -> None:
        """Verify ModelCircuitBreaker is importable from infrastructure."""
        from omnibase_core.infrastructure import ModelCircuitBreaker

        assert isinstance(ModelCircuitBreaker, type), (
            "ModelCircuitBreaker should be a type"
        )

    def test_infrastructure_compute_cache_import(self) -> None:
        """Verify ModelComputeCache is importable from infrastructure."""
        from omnibase_core.infrastructure import ModelComputeCache

        assert isinstance(ModelComputeCache, type), "ModelComputeCache should be a type"

    def test_infrastructure_effect_transaction_import(self) -> None:
        """Verify ModelEffectTransaction is importable from infrastructure."""
        from omnibase_core.infrastructure import ModelEffectTransaction

        assert isinstance(ModelEffectTransaction, type), (
            "ModelEffectTransaction should be a type"
        )

    def test_infrastructure_all_models_combined_import(self) -> None:
        """Verify all infrastructure models can be imported together."""
        from omnibase_core.infrastructure import (
            ModelCircuitBreaker,
            ModelComputeCache,
            ModelEffectTransaction,
            NodeBase,
            NodeCoreBase,
        )

        # All should be types
        for cls in [
            NodeBase,
            NodeCoreBase,
            ModelCircuitBreaker,
            ModelComputeCache,
            ModelEffectTransaction,
        ]:
            assert isinstance(cls, type), f"{cls.__name__} should be a type"


@pytest.mark.unit
class TestCircularImportPrevention:
    """Verify import order doesn't cause circular import issues."""

    def test_no_circular_imports_nodes_then_infrastructure(self) -> None:
        """Verify importing nodes then infrastructure doesn't cause issues."""
        from omnibase_core.infrastructure import NodeBase, NodeCoreBase
        from omnibase_core.nodes import NodeCompute, NodeEffect

        # If we get here without ImportError, circular imports are prevented
        assert NodeCompute is not None
        assert NodeEffect is not None
        assert NodeBase is not None
        assert NodeCoreBase is not None

    def test_no_circular_imports_infrastructure_then_nodes(self) -> None:
        """Verify importing infrastructure then nodes doesn't cause issues."""
        from omnibase_core.infrastructure import NodeBase, NodeCoreBase
        from omnibase_core.nodes import NodeCompute, NodeEffect

        # If we get here without ImportError, circular imports are prevented
        assert NodeBase is not None
        assert NodeCoreBase is not None
        assert NodeCompute is not None
        assert NodeEffect is not None

    def test_no_circular_imports_interleaved(self) -> None:
        """Verify interleaved imports don't cause circular import issues."""
        from omnibase_core.infrastructure import (
            ModelCircuitBreaker,
            NodeBase,
            NodeCoreBase,
        )
        from omnibase_core.nodes import ModelComputeInput, NodeCompute, NodeEffect

        # All should be accessible
        assert NodeCoreBase is not None
        assert NodeCompute is not None
        assert NodeBase is not None
        assert NodeEffect is not None
        assert ModelCircuitBreaker is not None
        assert ModelComputeInput is not None

    def test_no_circular_imports_models_with_nodes(self) -> None:
        """Verify model imports with node imports don't cause issues."""
        from omnibase_core.nodes import (
            ModelComputeInput,
            ModelComputeOutput,
            ModelEffectInput,
            ModelEffectOutput,
            ModelOrchestratorInput,
            ModelOrchestratorOutput,
            ModelReducerInput,
            ModelReducerOutput,
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        # All should be accessible without circular import issues
        assert all(
            cls is not None
            for cls in [
                ModelComputeInput,
                ModelComputeOutput,
                NodeCompute,
                ModelEffectInput,
                ModelEffectOutput,
                NodeEffect,
                ModelReducerInput,
                ModelReducerOutput,
                NodeReducer,
                ModelOrchestratorInput,
                ModelOrchestratorOutput,
                NodeOrchestrator,
            ]
        )


@pytest.mark.unit
class TestNodesModuleAllExports:
    """Verify __all__ exports match documented API."""

    def test_nodes_module_has_all_defined(self) -> None:
        """Verify nodes module has __all__ defined."""
        from omnibase_core import nodes

        assert hasattr(nodes, "__all__"), "nodes module should define __all__"
        assert isinstance(nodes.__all__, list), "__all__ should be a list"

    def test_nodes_module_all_contains_core_nodes(self) -> None:
        """Verify __all__ contains core node classes."""
        from omnibase_core import nodes

        expected_nodes = [
            "NodeCompute",
            "NodeEffect",
            "NodeReducer",
            "NodeOrchestrator",
        ]
        for node_name in expected_nodes:
            assert node_name in nodes.__all__, f"{node_name} should be in nodes.__all__"

    def test_nodes_module_all_contains_io_models(self) -> None:
        """Verify __all__ contains I/O model classes."""
        from omnibase_core import nodes

        expected_models = [
            "ModelComputeInput",
            "ModelComputeOutput",
            "ModelEffectInput",
            "ModelEffectOutput",
            "ModelReducerInput",
            "ModelReducerOutput",
            "ModelOrchestratorInput",
            "ModelOrchestratorOutput",
        ]
        for model_name in expected_models:
            assert model_name in nodes.__all__, (
                f"{model_name} should be in nodes.__all__"
            )

    def test_nodes_module_all_exports_are_accessible(self) -> None:
        """Verify all items in __all__ are actually importable."""
        from omnibase_core import nodes

        for export_name in nodes.__all__:
            assert hasattr(nodes, export_name), (
                f"{export_name} in __all__ but not accessible"
            )
            export_obj = getattr(nodes, export_name)
            assert export_obj is not None, f"{export_name} is None"


@pytest.mark.unit
class TestInfrastructureModuleAllExports:
    """Verify infrastructure module __all__ exports match documented API."""

    def test_infrastructure_module_has_all_defined(self) -> None:
        """Verify infrastructure module has __all__ defined."""
        from omnibase_core import infrastructure

        assert hasattr(infrastructure, "__all__"), (
            "infrastructure module should define __all__"
        )
        assert isinstance(infrastructure.__all__, list), "__all__ should be a list"

    def test_infrastructure_module_all_contains_base_classes(self) -> None:
        """Verify __all__ contains base classes."""
        from omnibase_core import infrastructure

        expected_bases = ["NodeBase", "NodeCoreBase"]
        for base_name in expected_bases:
            assert base_name in infrastructure.__all__, (
                f"{base_name} should be in infrastructure.__all__"
            )

    def test_infrastructure_module_all_contains_infrastructure_models(self) -> None:
        """Verify __all__ contains infrastructure model classes."""
        from omnibase_core import infrastructure

        expected_models = [
            "ModelCircuitBreaker",
            "ModelComputeCache",
            "ModelEffectTransaction",
        ]
        for model_name in expected_models:
            assert model_name in infrastructure.__all__, (
                f"{model_name} should be in infrastructure.__all__"
            )

    def test_infrastructure_module_all_exports_are_accessible(self) -> None:
        """Verify all items in __all__ are actually importable."""
        from omnibase_core import infrastructure

        for export_name in infrastructure.__all__:
            assert hasattr(infrastructure, export_name), (
                f"{export_name} in __all__ but not accessible"
            )
            export_obj = getattr(infrastructure, export_name)
            assert export_obj is not None, f"{export_name} is None"


@pytest.mark.unit
class TestImportPathConsistency:
    """Verify imports from different paths resolve to the same objects."""

    def test_effect_transaction_import_consistency(self) -> None:
        """Verify ModelEffectTransaction from nodes and infrastructure are the same."""
        from omnibase_core.infrastructure import (
            ModelEffectTransaction as InfraEffectTransaction,
        )
        from omnibase_core.nodes import ModelEffectTransaction as NodesEffectTransaction

        # Should be the exact same class
        assert NodesEffectTransaction is InfraEffectTransaction, (
            "ModelEffectTransaction from nodes and infrastructure should be identical"
        )

    def test_node_classes_inherit_from_infrastructure_bases(self) -> None:
        """Verify node classes properly inherit from infrastructure base classes."""
        from omnibase_core.infrastructure import NodeCoreBase
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        # All node classes should inherit from NodeCoreBase
        assert issubclass(NodeCompute, NodeCoreBase), (
            "NodeCompute should inherit from NodeCoreBase"
        )
        assert issubclass(NodeEffect, NodeCoreBase), (
            "NodeEffect should inherit from NodeCoreBase"
        )
        assert issubclass(NodeReducer, NodeCoreBase), (
            "NodeReducer should inherit from NodeCoreBase"
        )
        assert issubclass(NodeOrchestrator, NodeCoreBase), (
            "NodeOrchestrator should inherit from NodeCoreBase"
        )
