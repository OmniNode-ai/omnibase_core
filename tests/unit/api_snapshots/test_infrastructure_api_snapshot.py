# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pre-refactor API snapshot tests for omnibase_core.infrastructure module.

These tests capture the public API surface before v0.4.0 refactoring.
If these tests fail due to intentional breaking changes, update them
in the same PR with a migration note in the changelog.

Module: omnibase_core.infrastructure
Purpose: Node bases and infrastructure services for ONEX framework

Pre-refactor exports (v0.2.0):
-----------------------------
- NodeBase: Workflow-oriented node base with LlamaIndex integration
- NodeCoreBase: Foundation for 4-node architecture (inherits from ABC)
  NOTE: NodeBase and NodeCoreBase are INDEPENDENT base classes, not in an
  inheritance relationship. NodeBase is for workflow nodes, NodeCoreBase
  is for the 4-node architecture (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR).
- ModelCircuitBreaker: Circuit breaker pattern for fault tolerance
- ModelComputeCache: Caching for compute operations
- ModelEffectTransaction: Transaction support for effect operations
"""

import inspect

import pytest


@pytest.mark.unit
class TestInfrastructureAPISnapshot:
    """Snapshot tests for infrastructure module public API.

    These tests verify that the public API exports match the pre-refactor
    snapshot. Any changes to __all__ exports will cause these tests to fail,
    ensuring that API changes are intentional and documented.
    """

    # ==========================================================================
    # Pre-refactor API snapshot (v0.2.0)
    # ==========================================================================
    # This set represents the exact public API at the time of snapshot creation.
    # DO NOT modify this set unless you are intentionally changing the public API.
    # If you need to update this snapshot, document the change in CHANGELOG.md.
    # ==========================================================================
    EXPECTED_EXPORTS = frozenset(
        {
            # Node base classes
            "NodeBase",
            "NodeCoreBase",
            # Infrastructure models (re-exported for convenience)
            "ModelCircuitBreaker",
            "ModelComputeCache",
            "ModelEffectTransaction",
            # Cache backends (OMN-1188)
            "BackendCacheRedis",
            "REDIS_AVAILABLE",
            # Execution sequencing (v0.4.0+)
            "ModelExecutionPlan",
            "ModelPhaseStep",
            "create_execution_plan",
        }
    )

    def test_infrastructure_all_defined(self) -> None:
        """Test that __all__ is defined in infrastructure module."""
        from omnibase_core import infrastructure

        assert hasattr(infrastructure, "__all__"), (
            "infrastructure module must define __all__ to explicitly declare "
            "its public API surface"
        )

    def test_infrastructure_exports_snapshot(self) -> None:
        """Verify public API exports match pre-refactor snapshot.

        This test will fail if:
        1. An export is removed from __all__ (breaking change)
        2. An export is added to __all__ (API expansion, may be intentional)
        3. An export is renamed (breaking change)

        If this test fails due to intentional changes, update EXPECTED_EXPORTS
        and document the change in CHANGELOG.md with migration notes.
        """
        from omnibase_core import infrastructure

        actual_exports = frozenset(infrastructure.__all__)

        # Check for removed exports (breaking change)
        removed = self.EXPECTED_EXPORTS - actual_exports
        assert not removed, (
            f"BREAKING CHANGE: Exports removed from infrastructure.__all__: {removed}\n"
            f"If intentional, update EXPECTED_EXPORTS and add migration notes to CHANGELOG.md"
        )

        # Check for added exports (API expansion)
        added = actual_exports - self.EXPECTED_EXPORTS
        assert not added, (
            f"API EXPANSION: New exports added to infrastructure.__all__: {added}\n"
            f"If intentional, update EXPECTED_EXPORTS in this test file"
        )

        # Exact match verification
        assert actual_exports == self.EXPECTED_EXPORTS, (
            f"infrastructure.__all__ does not match pre-refactor snapshot.\n"
            f"Expected: {sorted(self.EXPECTED_EXPORTS)}\n"
            f"Actual: {sorted(actual_exports)}"
        )

    def test_infrastructure_exports_accessible(self) -> None:
        """Verify all exports in __all__ are actually accessible.

        This ensures that __all__ is not lying - every declared export
        must be importable and not None.
        """
        from omnibase_core import infrastructure

        for name in infrastructure.__all__:
            assert hasattr(infrastructure, name), (
                f"Export '{name}' declared in __all__ but not accessible. "
                f"The export may be missing an import statement."
            )
            export_obj = getattr(infrastructure, name)
            assert export_obj is not None, (
                f"Export '{name}' is None. This may indicate a failed import "
                f"or initialization error."
            )

    def test_infrastructure_no_private_exports(self) -> None:
        """Verify no private modules or attributes are exposed in __all__.

        Private items (starting with _) should never be in __all__ as they
        are internal implementation details.
        """
        from omnibase_core import infrastructure

        private_exports = [
            name for name in infrastructure.__all__ if name.startswith("_")
        ]
        assert not private_exports, (
            f"Private items exposed in __all__: {private_exports}\n"
            f"Remove these from __all__ - they are internal implementation details."
        )


@pytest.mark.unit
class TestInfrastructureExportTypes:
    """Verify the types and inheritance of exported classes.

    These tests ensure that the exported classes maintain their expected
    type hierarchy and relationships.
    """

    def test_node_base_is_class(self) -> None:
        """Verify NodeBase is a class."""
        from omnibase_core.infrastructure import NodeBase

        assert isinstance(NodeBase, type), "NodeBase must be a class"

    def test_node_core_base_is_class(self) -> None:
        """Verify NodeCoreBase is a class."""
        from omnibase_core.infrastructure import NodeCoreBase

        assert isinstance(NodeCoreBase, type), "NodeCoreBase must be a class"

    def test_node_core_base_is_abc(self) -> None:
        """Verify NodeCoreBase inherits from ABC.

        NodeCoreBase is the foundation for the 4-node architecture and
        inherits from ABC to enforce abstract method implementation.
        """
        from abc import ABC

        from omnibase_core.infrastructure import NodeCoreBase

        assert issubclass(NodeCoreBase, ABC), (
            "NodeCoreBase must inherit from ABC. "
            "This is required for the abstract base class pattern."
        )

    def test_node_base_and_node_core_base_are_independent(self) -> None:
        """Verify NodeBase and NodeCoreBase are independent base classes.

        IMPORTANT: These are separate, independent base classes:
        - NodeBase: Workflow-oriented node with LlamaIndex integration
        - NodeCoreBase: Foundation for 4-node architecture (COMPUTE, EFFECT, etc.)

        They should NOT be in an inheritance relationship.
        """
        from omnibase_core.infrastructure import NodeBase, NodeCoreBase

        # Verify they are independent (neither inherits from the other)
        assert not issubclass(NodeCoreBase, NodeBase), (
            "NodeCoreBase should NOT inherit from NodeBase. "
            "These are independent base classes for different purposes."
        )
        assert not issubclass(NodeBase, NodeCoreBase), (
            "NodeBase should NOT inherit from NodeCoreBase. "
            "These are independent base classes for different purposes."
        )

    def test_model_circuit_breaker_is_class(self) -> None:
        """Verify ModelCircuitBreaker is a class."""
        from omnibase_core.infrastructure import ModelCircuitBreaker

        assert isinstance(ModelCircuitBreaker, type), (
            "ModelCircuitBreaker must be a class"
        )

    def test_model_compute_cache_is_class(self) -> None:
        """Verify ModelComputeCache is a class."""
        from omnibase_core.infrastructure import ModelComputeCache

        assert isinstance(ModelComputeCache, type), "ModelComputeCache must be a class"

    def test_model_effect_transaction_is_class(self) -> None:
        """Verify ModelEffectTransaction is a class."""
        from omnibase_core.infrastructure import ModelEffectTransaction

        assert isinstance(ModelEffectTransaction, type), (
            "ModelEffectTransaction must be a class"
        )

    def test_model_execution_plan_is_class(self) -> None:
        """Verify ModelExecutionPlan is a class."""
        from omnibase_core.infrastructure import ModelExecutionPlan

        assert isinstance(ModelExecutionPlan, type), (
            "ModelExecutionPlan must be a class"
        )

    def test_model_phase_step_is_class(self) -> None:
        """Verify ModelPhaseStep is a class."""
        from omnibase_core.infrastructure import ModelPhaseStep

        assert isinstance(ModelPhaseStep, type), "ModelPhaseStep must be a class"

    def test_create_execution_plan_is_function(self) -> None:
        """Verify create_execution_plan is a function."""
        from omnibase_core.infrastructure import create_execution_plan

        assert callable(create_execution_plan), "create_execution_plan must be callable"

    def test_backend_cache_redis_is_class(self) -> None:
        """Verify BackendCacheRedis is a class."""
        from omnibase_core.infrastructure import BackendCacheRedis

        assert isinstance(BackendCacheRedis, type), "BackendCacheRedis must be a class"

    def test_redis_available_is_bool(self) -> None:
        """Verify REDIS_AVAILABLE is a boolean."""
        from omnibase_core.infrastructure import REDIS_AVAILABLE

        assert isinstance(REDIS_AVAILABLE, bool), "REDIS_AVAILABLE must be a boolean"


@pytest.mark.unit
class TestInfrastructureImportPaths:
    """Verify that exports can be imported via the infrastructure module.

    These tests ensure that the re-export pattern works correctly and
    users can import from the infrastructure module directly.
    """

    def test_import_node_base_from_infrastructure(self) -> None:
        """Test that NodeBase can be imported from infrastructure."""
        from omnibase_core.infrastructure import NodeBase

        assert NodeBase is not None

    def test_import_node_core_base_from_infrastructure(self) -> None:
        """Test that NodeCoreBase can be imported from infrastructure."""
        from omnibase_core.infrastructure import NodeCoreBase

        assert NodeCoreBase is not None

    def test_import_model_circuit_breaker_from_infrastructure(self) -> None:
        """Test that ModelCircuitBreaker can be imported from infrastructure."""
        from omnibase_core.infrastructure import ModelCircuitBreaker

        assert ModelCircuitBreaker is not None

    def test_import_model_compute_cache_from_infrastructure(self) -> None:
        """Test that ModelComputeCache can be imported from infrastructure."""
        from omnibase_core.infrastructure import ModelComputeCache

        assert ModelComputeCache is not None

    def test_import_model_effect_transaction_from_infrastructure(self) -> None:
        """Test that ModelEffectTransaction can be imported from infrastructure."""
        from omnibase_core.infrastructure import ModelEffectTransaction

        assert ModelEffectTransaction is not None

    def test_import_model_execution_plan_from_infrastructure(self) -> None:
        """Test that ModelExecutionPlan can be imported from infrastructure."""
        from omnibase_core.infrastructure import ModelExecutionPlan

        assert ModelExecutionPlan is not None

    def test_import_model_phase_step_from_infrastructure(self) -> None:
        """Test that ModelPhaseStep can be imported from infrastructure."""
        from omnibase_core.infrastructure import ModelPhaseStep

        assert ModelPhaseStep is not None

    def test_import_create_execution_plan_from_infrastructure(self) -> None:
        """Test that create_execution_plan can be imported from infrastructure."""
        from omnibase_core.infrastructure import create_execution_plan

        assert create_execution_plan is not None
        assert callable(create_execution_plan)

    def test_import_backend_cache_redis_from_infrastructure(self) -> None:
        """Test that BackendCacheRedis can be imported from infrastructure."""
        from omnibase_core.infrastructure import BackendCacheRedis

        assert BackendCacheRedis is not None

    def test_import_redis_available_from_infrastructure(self) -> None:
        """Test that REDIS_AVAILABLE can be imported from infrastructure."""
        from omnibase_core.infrastructure import REDIS_AVAILABLE

        assert REDIS_AVAILABLE is not None

    def test_infrastructure_module_import(self) -> None:
        """Test that the infrastructure module itself can be imported."""
        from omnibase_core import infrastructure

        assert infrastructure is not None
        assert hasattr(infrastructure, "__all__")


@pytest.mark.unit
class TestInfrastructureReexportConsistency:
    """Verify that re-exported models are the same objects as their originals.

    This ensures that importing from infrastructure gives you the exact same
    class objects as importing from their original locations.
    """

    def test_model_circuit_breaker_reexport_identity(self) -> None:
        """Verify ModelCircuitBreaker re-export is identical to original."""
        from omnibase_core.infrastructure import ModelCircuitBreaker as ReexportedClass
        from omnibase_core.models.configuration.model_circuit_breaker import (
            ModelCircuitBreaker as OriginalClass,
        )

        assert ReexportedClass is OriginalClass, (
            "ModelCircuitBreaker re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )

    def test_model_compute_cache_reexport_identity(self) -> None:
        """Verify ModelComputeCache re-export is identical to original."""
        from omnibase_core.infrastructure import ModelComputeCache as ReexportedClass
        from omnibase_core.models.infrastructure.model_compute_cache import (
            ModelComputeCache as OriginalClass,
        )

        assert ReexportedClass is OriginalClass, (
            "ModelComputeCache re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )

    def test_model_effect_transaction_reexport_identity(self) -> None:
        """Verify ModelEffectTransaction re-export is identical to original."""
        from omnibase_core.infrastructure import (
            ModelEffectTransaction as ReexportedClass,
        )
        from omnibase_core.models.infrastructure.model_effect_transaction import (
            ModelEffectTransaction as OriginalClass,
        )

        assert ReexportedClass is OriginalClass, (
            "ModelEffectTransaction re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )

    def test_model_execution_plan_reexport_identity(self) -> None:
        """Verify ModelExecutionPlan re-export is identical to original."""
        from omnibase_core.infrastructure import ModelExecutionPlan as ReexportedClass
        from omnibase_core.models.execution.model_execution_plan import (
            ModelExecutionPlan as OriginalClass,
        )

        assert ReexportedClass is OriginalClass, (
            "ModelExecutionPlan re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )

    def test_model_phase_step_reexport_identity(self) -> None:
        """Verify ModelPhaseStep re-export is identical to original."""
        from omnibase_core.infrastructure import ModelPhaseStep as ReexportedClass
        from omnibase_core.models.execution.model_phase_step import (
            ModelPhaseStep as OriginalClass,
        )

        assert ReexportedClass is OriginalClass, (
            "ModelPhaseStep re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )

    def test_create_execution_plan_reexport_identity(self) -> None:
        """Verify create_execution_plan re-export is identical to original."""
        from omnibase_core.infrastructure import (
            create_execution_plan as reexported_func,
        )
        from omnibase_core.infrastructure.execution.infra_phase_sequencer import (
            create_execution_plan as original_func,
        )

        assert reexported_func is original_func, (
            "create_execution_plan re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )

    def test_backend_cache_redis_reexport_identity(self) -> None:
        """Verify BackendCacheRedis re-export is identical to original."""
        from omnibase_core.backends.cache import BackendCacheRedis as OriginalClass
        from omnibase_core.infrastructure import BackendCacheRedis as ReexportedClass

        assert ReexportedClass is OriginalClass, (
            "BackendCacheRedis re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )

    def test_redis_available_reexport_identity(self) -> None:
        """Verify REDIS_AVAILABLE re-export is identical to original."""
        from omnibase_core.backends.cache import REDIS_AVAILABLE as ORIGINAL_VALUE
        from omnibase_core.infrastructure import REDIS_AVAILABLE as REEXPORTED_VALUE

        assert REEXPORTED_VALUE is ORIGINAL_VALUE, (
            "REDIS_AVAILABLE re-export must be identical to original. "
            "Check the import in infrastructure/__init__.py"
        )


@pytest.mark.unit
class TestAbstractMethodEnforcement:
    """Tests for abstract method enforcement in NodeCoreBase hierarchy.

    These tests verify that:
    1. NodeCoreBase properly declares abstract methods
    2. Abstract methods use @abstractmethod decorator
    3. Concrete node classes properly implement all abstract methods
    4. Attempting to instantiate abstract classes directly raises TypeError

    This ensures the contract between base classes and implementations
    is properly enforced at the Python level.
    """

    def test_node_core_base_is_abstract(self) -> None:
        """Verify NodeCoreBase is an abstract class and cannot be instantiated.

        NodeCoreBase inherits from ABC and declares abstract methods.
        Attempting to instantiate it directly should raise TypeError.
        """
        from unittest.mock import MagicMock

        from omnibase_core.infrastructure import NodeCoreBase

        # Verify class is abstract using inspect
        assert inspect.isabstract(NodeCoreBase), (
            "NodeCoreBase must be an abstract class. "
            "Ensure it inherits from ABC and has @abstractmethod decorated methods."
        )

        # Verify instantiation raises TypeError
        mock_container = MagicMock()
        with pytest.raises(TypeError) as exc_info:
            NodeCoreBase(mock_container)

        # Verify error message mentions abstract method
        error_message = str(exc_info.value)
        assert "abstract" in error_message.lower() or "process" in error_message, (
            f"TypeError should mention abstract method. Got: {error_message}"
        )

    def test_node_core_base_process_is_abstract(self) -> None:
        """Verify the 'process' method is declared as abstract in NodeCoreBase.

        The process method is the core interface that all nodes must implement.
        It must be decorated with @abstractmethod.
        """
        from omnibase_core.infrastructure import NodeCoreBase

        # Get the process method from NodeCoreBase
        process_method = getattr(NodeCoreBase, "process", None)
        assert process_method is not None, "NodeCoreBase must have a 'process' method"

        # Check if method has __isabstractmethod__ attribute set to True
        is_abstract = getattr(process_method, "__isabstractmethod__", False)
        assert is_abstract, (
            "NodeCoreBase.process must be decorated with @abstractmethod. "
            "This ensures concrete nodes are required to implement it."
        )

    def test_node_core_base_abstract_methods_snapshot(self) -> None:
        """Verify the set of abstract methods in NodeCoreBase matches snapshot.

        Pre-refactor snapshot: {'process'} is the only abstract method.

        If this test fails, it means abstract methods were added or removed,
        which may be a breaking change for existing node implementations.
        """
        from omnibase_core.infrastructure import NodeCoreBase

        # Get all abstract methods from the class
        abstract_methods = set()
        for name, method in inspect.getmembers(NodeCoreBase):
            if getattr(method, "__isabstractmethod__", False):
                abstract_methods.add(name)

        expected_abstract_methods = {"process"}
        assert abstract_methods == expected_abstract_methods, (
            f"Abstract methods in NodeCoreBase changed. "
            f"Expected: {expected_abstract_methods}, Got: {abstract_methods}. "
            f"Adding/removing abstract methods may break existing implementations."
        )

    def test_concrete_nodes_implement_process(self) -> None:
        """Verify all concrete node classes implement the process method.

        All 4-node architecture classes must provide a concrete implementation
        of the abstract process method from NodeCoreBase.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            # Verify class is NOT abstract (can be instantiated)
            assert not inspect.isabstract(node_class), (
                f"{node_class.__name__} must not be abstract. "
                f"Ensure it implements all abstract methods from NodeCoreBase."
            )

            # Verify process method exists and is not abstract
            process_method = getattr(node_class, "process", None)
            assert process_method is not None, (
                f"{node_class.__name__} must have a 'process' method"
            )

            is_abstract = getattr(process_method, "__isabstractmethod__", False)
            assert not is_abstract, (
                f"{node_class.__name__}.process must be a concrete implementation, "
                f"not an abstract method."
            )

    def test_concrete_nodes_process_is_async(self) -> None:
        """Verify all concrete node process methods are async.

        The process method signature requires async for consistent behavior.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            process_method = getattr(node_class, "process", None)
            assert process_method is not None, (
                f"{node_class.__name__} must have a 'process' method"
            )

            # Check if the method is a coroutine function
            assert inspect.iscoroutinefunction(process_method), (
                f"{node_class.__name__}.process must be an async method. "
                f"This is required for consistent node behavior."
            )

    def test_incomplete_node_implementation_raises_type_error(self) -> None:
        """Verify that incomplete node implementations cannot be instantiated.

        A class inheriting from NodeCoreBase that does not implement process
        should raise TypeError when instantiated.
        """
        from unittest.mock import MagicMock

        from omnibase_core.infrastructure import NodeCoreBase

        # Define an incomplete node class that doesn't implement process
        class IncompleteNode(NodeCoreBase):  # type: ignore[misc]
            """A node that intentionally does not implement process."""

        # Verify the class is still abstract
        assert inspect.isabstract(IncompleteNode), (
            "IncompleteNode should be abstract since it doesn't implement process"
        )

        # Verify instantiation raises TypeError
        mock_container = MagicMock()
        with pytest.raises(TypeError) as exc_info:
            IncompleteNode(mock_container)

        error_message = str(exc_info.value)
        assert "process" in error_message, (
            f"TypeError should mention missing 'process' method. Got: {error_message}"
        )

    def test_complete_node_implementation_can_be_instantiated(self) -> None:
        """Verify that a complete node implementation can be instantiated.

        A class inheriting from NodeCoreBase that implements all abstract
        methods should be instantiable without TypeError.
        """
        from typing import Any
        from unittest.mock import MagicMock

        from omnibase_core.infrastructure import NodeCoreBase

        # Define a complete node class
        class CompleteNode(NodeCoreBase):  # type: ignore[misc]
            """A node that properly implements process."""

            async def process(self, input_data: Any) -> Any:
                """Concrete implementation of process."""
                return input_data

        # Verify the class is NOT abstract
        assert not inspect.isabstract(CompleteNode), (
            "CompleteNode should not be abstract since it implements process"
        )

        # Verify instantiation works
        mock_container = MagicMock()
        mock_container.get_service = MagicMock()

        # This should not raise TypeError
        node = CompleteNode(mock_container)
        assert node is not None
        assert node.container is mock_container
