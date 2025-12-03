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

        assert isinstance(
            ModelCircuitBreaker, type
        ), "ModelCircuitBreaker must be a class"

    def test_model_compute_cache_is_class(self) -> None:
        """Verify ModelComputeCache is a class."""
        from omnibase_core.infrastructure import ModelComputeCache

        assert isinstance(ModelComputeCache, type), "ModelComputeCache must be a class"

    def test_model_effect_transaction_is_class(self) -> None:
        """Verify ModelEffectTransaction is a class."""
        from omnibase_core.infrastructure import ModelEffectTransaction

        assert isinstance(
            ModelEffectTransaction, type
        ), "ModelEffectTransaction must be a class"


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
