"""
Tests for node protocol compliance (OMN-662).

This module verifies that node implementations satisfy their corresponding
protocols via isinstance checks. The protocols are @runtime_checkable,
enabling duck typing verification.

Tests cover:
- NodeCompute implements ProtocolCompute
- NodeEffect implements ProtocolEffect
- NodeOrchestrator implements ProtocolOrchestrator

Related:
    - PR #267: Node protocol definitions for ONEX Four-Node Architecture
    - OMN-662: Node Protocol Definitions
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import NodeCompute, NodeEffect, NodeOrchestrator
from omnibase_core.protocols import (
    ProtocolCompute,
    ProtocolEffect,
    ProtocolOrchestrator,
)


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing.

    Returns:
        ModelONEXContainer mock with required service methods.
    """
    container = MagicMock(spec=ModelONEXContainer)
    container.get_service = MagicMock(return_value=MagicMock())
    container.get_service_optional = MagicMock(return_value=None)

    # Mock compute cache config (required by NodeCompute)
    mock_cache_config = MagicMock()
    mock_cache_config.get_ttl_minutes = MagicMock(return_value=30)
    container.compute_cache_config = mock_cache_config

    return container


@pytest.mark.unit
class TestNodeComputeProtocolCompliance:
    """Tests verifying NodeCompute implements ProtocolCompute."""

    def test_node_compute_isinstance_protocol_compute(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify NodeCompute satisfies ProtocolCompute via isinstance check.

        This test confirms that NodeCompute implements the ProtocolCompute
        interface, enabling type-safe usage as a compute node in workflows.
        """
        # Arrange: Create a NodeCompute instance
        node: NodeCompute[Any, Any] = NodeCompute(mock_container)

        # Act & Assert: Verify protocol compliance
        assert isinstance(node, ProtocolCompute), (
            "NodeCompute must implement ProtocolCompute for ONEX compliance"
        )

    def test_node_compute_has_required_methods(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify NodeCompute has all methods required by ProtocolCompute."""
        node: NodeCompute[Any, Any] = NodeCompute(mock_container)

        # Verify required methods exist and are callable
        assert hasattr(node, "process"), "NodeCompute must have process method"
        assert callable(node.process), "process must be callable"

        assert hasattr(node, "execute_compute"), (
            "NodeCompute must have execute_compute method"
        )
        assert callable(node.execute_compute), "execute_compute must be callable"

        assert hasattr(node, "register_computation"), (
            "NodeCompute must have register_computation method"
        )
        assert callable(node.register_computation), (
            "register_computation must be callable"
        )

        assert hasattr(node, "get_computation_metrics"), (
            "NodeCompute must have get_computation_metrics method"
        )
        assert callable(node.get_computation_metrics), (
            "get_computation_metrics must be callable"
        )


@pytest.mark.unit
class TestNodeEffectProtocolCompliance:
    """Tests verifying NodeEffect implements ProtocolEffect."""

    def test_node_effect_isinstance_protocol_effect(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify NodeEffect satisfies ProtocolEffect via isinstance check.

        This test confirms that NodeEffect implements the ProtocolEffect
        interface, enabling type-safe usage as an effect node for external I/O.
        """
        # Arrange: Create a NodeEffect instance
        node = NodeEffect(mock_container)

        # Act & Assert: Verify protocol compliance
        assert isinstance(node, ProtocolEffect), (
            "NodeEffect must implement ProtocolEffect for ONEX compliance"
        )

    def test_node_effect_has_required_methods(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify NodeEffect has all methods required by ProtocolEffect."""
        node = NodeEffect(mock_container)

        # Verify required methods exist and are callable
        assert hasattr(node, "process"), "NodeEffect must have process method"
        assert callable(node.process), "process must be callable"

        assert hasattr(node, "get_circuit_breaker"), (
            "NodeEffect must have get_circuit_breaker method"
        )
        assert callable(node.get_circuit_breaker), (
            "get_circuit_breaker must be callable"
        )

        assert hasattr(node, "reset_circuit_breakers"), (
            "NodeEffect must have reset_circuit_breakers method"
        )
        assert callable(node.reset_circuit_breakers), (
            "reset_circuit_breakers must be callable"
        )

        assert hasattr(node, "get_registered_handlers"), (
            "NodeEffect must have get_registered_handlers method"
        )
        assert callable(node.get_registered_handlers), (
            "get_registered_handlers must be callable"
        )

        assert hasattr(node, "get_handler_registration_report"), (
            "NodeEffect must have get_handler_registration_report method"
        )
        assert callable(node.get_handler_registration_report), (
            "get_handler_registration_report must be callable"
        )


@pytest.mark.unit
class TestNodeOrchestratorProtocolCompliance:
    """Tests verifying NodeOrchestrator implements ProtocolOrchestrator."""

    def test_node_orchestrator_isinstance_protocol_orchestrator(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify NodeOrchestrator satisfies ProtocolOrchestrator via isinstance check.

        This test confirms that NodeOrchestrator implements the ProtocolOrchestrator
        interface, enabling type-safe usage for workflow coordination.
        """
        # Arrange: Create a NodeOrchestrator instance
        node = NodeOrchestrator(mock_container)

        # Act & Assert: Verify protocol compliance
        assert isinstance(node, ProtocolOrchestrator), (
            "NodeOrchestrator must implement ProtocolOrchestrator for ONEX compliance"
        )

    def test_node_orchestrator_has_required_methods(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify NodeOrchestrator has all methods required by ProtocolOrchestrator."""
        node = NodeOrchestrator(mock_container)

        # Verify required methods exist and are callable
        assert hasattr(node, "process"), "NodeOrchestrator must have process method"
        assert callable(node.process), "process must be callable"

        assert hasattr(node, "validate_contract"), (
            "NodeOrchestrator must have validate_contract method"
        )
        assert callable(node.validate_contract), "validate_contract must be callable"

        assert hasattr(node, "validate_workflow_steps"), (
            "NodeOrchestrator must have validate_workflow_steps method"
        )
        assert callable(node.validate_workflow_steps), (
            "validate_workflow_steps must be callable"
        )

        assert hasattr(node, "get_execution_order_for_steps"), (
            "NodeOrchestrator must have get_execution_order_for_steps method"
        )
        assert callable(node.get_execution_order_for_steps), (
            "get_execution_order_for_steps must be callable"
        )

        assert hasattr(node, "snapshot_workflow_state"), (
            "NodeOrchestrator must have snapshot_workflow_state method"
        )
        assert callable(node.snapshot_workflow_state), (
            "snapshot_workflow_state must be callable"
        )

        assert hasattr(node, "restore_workflow_state"), (
            "NodeOrchestrator must have restore_workflow_state method"
        )
        assert callable(node.restore_workflow_state), (
            "restore_workflow_state must be callable"
        )

        assert hasattr(node, "get_workflow_snapshot"), (
            "NodeOrchestrator must have get_workflow_snapshot method"
        )
        assert callable(node.get_workflow_snapshot), (
            "get_workflow_snapshot must be callable"
        )


@pytest.mark.unit
class TestAllNodesProtocolCompliance:
    """Cross-cutting tests for all node protocol compliance."""

    def test_all_nodes_are_runtime_checkable(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify all node protocols support runtime isinstance checks.

        The @runtime_checkable decorator on protocols enables duck typing
        verification at runtime, which is essential for ONEX compliance.
        """
        # Create all node types
        compute_node: NodeCompute[Any, Any] = NodeCompute(mock_container)
        effect_node = NodeEffect(mock_container)
        orchestrator_node = NodeOrchestrator(mock_container)

        # Verify all protocols support isinstance checks
        # This will raise TypeError if protocols are not @runtime_checkable
        assert isinstance(compute_node, ProtocolCompute)
        assert isinstance(effect_node, ProtocolEffect)
        assert isinstance(orchestrator_node, ProtocolOrchestrator)

    def test_nodes_do_not_satisfy_wrong_protocols(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Verify nodes do not satisfy incorrect protocols.

        Each node type should only satisfy its corresponding protocol,
        not other node protocols. This ensures proper type separation.
        """
        compute_node: NodeCompute[Any, Any] = NodeCompute(mock_container)
        effect_node = NodeEffect(mock_container)
        orchestrator_node = NodeOrchestrator(mock_container)

        # NodeCompute should not satisfy Effect or Orchestrator protocols
        assert not isinstance(compute_node, ProtocolEffect), (
            "NodeCompute should not satisfy ProtocolEffect"
        )
        assert not isinstance(compute_node, ProtocolOrchestrator), (
            "NodeCompute should not satisfy ProtocolOrchestrator"
        )

        # NodeEffect should not satisfy Compute or Orchestrator protocols
        assert not isinstance(effect_node, ProtocolCompute), (
            "NodeEffect should not satisfy ProtocolCompute"
        )
        assert not isinstance(effect_node, ProtocolOrchestrator), (
            "NodeEffect should not satisfy ProtocolOrchestrator"
        )

        # NodeOrchestrator should not satisfy Compute or Effect protocols
        assert not isinstance(orchestrator_node, ProtocolCompute), (
            "NodeOrchestrator should not satisfy ProtocolCompute"
        )
        assert not isinstance(orchestrator_node, ProtocolEffect), (
            "NodeOrchestrator should not satisfy ProtocolEffect"
        )
