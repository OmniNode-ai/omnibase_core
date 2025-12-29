"""
Tests for node protocol compliance (OMN-662).

This module verifies that node implementations satisfy their corresponding
protocols via isinstance checks. The protocols are @runtime_checkable,
enabling duck typing verification.

Tests cover:
- NodeCompute implements ProtocolCompute
- NodeEffect implements ProtocolEffect
- NodeOrchestrator implements ProtocolOrchestrator
- Architectural invariants for ONEX four-node architecture

Related:
    - PR #267: Node protocol definitions for ONEX Four-Node Architecture
    - OMN-662: Node Protocol Definitions
"""

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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


@pytest.mark.unit
class TestArchitecturalInvariants:
    """Tests verifying ONEX architectural constraints on node types.

    These tests ensure that the ONEX four-node architecture's fundamental
    invariants are enforced at the model level. The constraints tested here
    are critical for maintaining proper separation of concerns between
    coordination (ORCHESTRATOR) and transformation (COMPUTE) nodes.

    Related:
        - ONEX Four-Node Architecture documentation
        - OMN-941: Handler Output Model constraints
    """

    def test_orchestrator_cannot_return_typed_results(self) -> None:
        """Verify ORCHESTRATOR nodes cannot return typed results.

        CRITICAL CONSTRAINT: Orchestrators can only emit events and intents.
        Only COMPUTE nodes return typed results. This enforces separation
        between coordination (ORCHESTRATOR) and transformation (COMPUTE).

        The ModelHandlerOutput validator raises ModelOnexError when an
        ORCHESTRATOR node attempts to set a non-None result value.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        # Attempt to create ORCHESTRATOR output with typed result
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-orchestrator",
                node_kind=EnumNodeKind.ORCHESTRATOR,
                result={
                    "status": "done"
                },  # VIOLATION: orchestrators cannot return results
            )

        # Verify error message explains the constraint
        assert "ORCHESTRATOR cannot set result" in str(exc_info.value)
        assert "Only COMPUTE nodes return typed results" in str(exc_info.value)

    def test_orchestrator_can_emit_events_and_intents(self) -> None:
        """Verify ORCHESTRATOR nodes can emit events and intents (positive case).

        While orchestrators cannot return typed results, they CAN emit events
        and intents for workflow coordination purposes.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        # Create ORCHESTRATOR output with events and intents (valid)
        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="test-orchestrator",
            events=("mock_event",),
            intents=("mock_intent",),
        )

        # Verify output was created successfully
        assert output.node_kind == EnumNodeKind.ORCHESTRATOR
        assert output.result is None
        assert len(output.events) == 1
        assert len(output.intents) == 1

    def test_compute_can_return_typed_results(self) -> None:
        """Verify COMPUTE nodes can return typed results (positive case).

        COMPUTE nodes are pure transformations that MUST return typed results.
        This is the inverse of the ORCHESTRATOR constraint and demonstrates
        proper architectural separation.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        # Create COMPUTE output with typed result (valid)
        result_data = {"transformed": True, "count": 42}
        output = ModelHandlerOutput.for_compute(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="test-compute",
            result=result_data,
        )

        # Verify result is preserved
        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.result == result_data
        assert output.has_result() is True

    def test_compute_cannot_emit_events(self) -> None:
        """Verify COMPUTE nodes cannot emit events.

        COMPUTE nodes are pure transformations - if you need to emit events,
        use an EFFECT node instead. This maintains referential transparency.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-compute",
                node_kind=EnumNodeKind.COMPUTE,
                result={"data": "value"},
                events=("mock_event",),  # VIOLATION: compute cannot emit events
            )

        assert "COMPUTE cannot emit events" in str(exc_info.value)

    def test_protocol_asymmetry_execute_compute_vs_orchestrator(self) -> None:
        """Verify intentional asymmetry: Compute has execute_compute, Orchestrator doesn't.

        This asymmetry is documented in ProtocolOrchestrator's docstring.
        Orchestrators are reactive coordinators, not callable operations.

        Design Rationale:
        - COMPUTE nodes are INVOKED: They execute a single unit of work
          and return typed results. execute_compute(contract) is natural.

        - ORCHESTRATOR nodes are REACTIVE: They coordinate workflows by
          responding to events, commands, and state transitions. They should
          NOT have execute_orchestration() as it incorrectly implies they
          can be called like compute nodes.
        """
        # ProtocolCompute MUST have execute_compute method
        assert hasattr(ProtocolCompute, "execute_compute"), (
            "ProtocolCompute must have execute_compute method - "
            "COMPUTE nodes are invoked to perform single units of work"
        )

        # ProtocolOrchestrator intentionally does NOT have execute_orchestration
        assert not hasattr(ProtocolOrchestrator, "execute_orchestration"), (
            "ProtocolOrchestrator intentionally does NOT have execute_orchestration - "
            "orchestrators are reactive coordinators, not callable operations. "
            "See ProtocolOrchestrator docstring for design rationale."
        )

    def test_reducer_cannot_return_results(self) -> None:
        """Verify REDUCER nodes cannot return typed results.

        REDUCER nodes emit projections only (pure fold functions).
        They update read-optimized state projections, not return results.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-reducer",
                node_kind=EnumNodeKind.REDUCER,
                result={"state": "value"},  # VIOLATION: reducers cannot return results
            )

        assert "REDUCER cannot set result" in str(exc_info.value)

    def test_effect_cannot_return_results(self) -> None:
        """Verify EFFECT nodes cannot return typed results.

        EFFECT nodes emit events only (I/O boundary).
        They publish result events about external interactions, not return results.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-effect",
                node_kind=EnumNodeKind.EFFECT,
                result={
                    "response": "value"
                },  # VIOLATION: effects cannot return results
            )

        assert "EFFECT cannot set result" in str(exc_info.value)

    def test_effect_can_emit_events(self) -> None:
        """Verify EFFECT nodes can emit events (positive case).

        EFFECT nodes execute side effects and publish facts about those
        interactions via events.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        # Create EFFECT output with events (valid)
        output = ModelHandlerOutput.for_effect(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="test-effect",
            events=("mock_event",),
        )

        # Verify output was created successfully
        assert output.node_kind == EnumNodeKind.EFFECT
        assert output.result is None
        assert len(output.events) == 1

    def test_effect_cannot_emit_intents(self) -> None:
        """Verify EFFECT nodes cannot emit intents.

        Only ORCHESTRATOR nodes can emit intents. Effects are I/O boundaries
        that emit events about external interactions.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-effect",
                node_kind=EnumNodeKind.EFFECT,
                intents=("mock_intent",),  # VIOLATION: effects cannot emit intents
            )

        assert "EFFECT cannot emit intents" in str(exc_info.value)

    def test_effect_cannot_emit_projections(self) -> None:
        """Verify EFFECT nodes cannot emit projections.

        Only REDUCER nodes can emit projections. Effects are I/O boundaries
        that emit events about external interactions.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-effect",
                node_kind=EnumNodeKind.EFFECT,
                projections=(
                    "mock_projection",
                ),  # VIOLATION: effects cannot emit projections
            )

        assert "EFFECT cannot emit projections" in str(exc_info.value)

    def test_reducer_can_emit_projections(self) -> None:
        """Verify REDUCER nodes can emit projections (positive case).

        REDUCER nodes are pure fold functions that update read-optimized
        state projections.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        # Create REDUCER output with projections (valid)
        output = ModelHandlerOutput.for_reducer(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="test-reducer",
            projections=("mock_projection",),
        )

        # Verify output was created successfully
        assert output.node_kind == EnumNodeKind.REDUCER
        assert output.result is None
        assert len(output.projections) == 1

    def test_reducer_cannot_emit_events(self) -> None:
        """Verify REDUCER nodes cannot emit events.

        REDUCER nodes are pure fold functions. They cannot emit events -
        only projections for read-optimized state.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-reducer",
                node_kind=EnumNodeKind.REDUCER,
                events=("mock_event",),  # VIOLATION: reducers cannot emit events
            )

        assert "REDUCER cannot emit events" in str(exc_info.value)

    def test_reducer_cannot_emit_intents(self) -> None:
        """Verify REDUCER nodes cannot emit intents.

        REDUCER nodes are pure fold functions. They cannot emit intents -
        only projections for read-optimized state.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-reducer",
                node_kind=EnumNodeKind.REDUCER,
                intents=("mock_intent",),  # VIOLATION: reducers cannot emit intents
            )

        assert "REDUCER cannot emit intents" in str(exc_info.value)

    def test_orchestrator_cannot_emit_projections(self) -> None:
        """Verify ORCHESTRATOR nodes cannot emit projections.

        ORCHESTRATOR nodes coordinate workflows via events and intents.
        Only REDUCER nodes can emit projections.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-orchestrator",
                node_kind=EnumNodeKind.ORCHESTRATOR,
                projections=(
                    "mock_projection",
                ),  # VIOLATION: orchestrators cannot emit projections
            )

        assert "ORCHESTRATOR cannot emit projections" in str(exc_info.value)

    def test_compute_cannot_emit_intents(self) -> None:
        """Verify COMPUTE nodes cannot emit intents.

        COMPUTE nodes are pure transformations that return results only.
        They cannot emit intents - use ORCHESTRATOR for workflow coordination.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-compute",
                node_kind=EnumNodeKind.COMPUTE,
                result={"data": "value"},
                intents=("mock_intent",),  # VIOLATION: compute cannot emit intents
            )

        assert "COMPUTE cannot emit intents" in str(exc_info.value)

    def test_compute_cannot_emit_projections(self) -> None:
        """Verify COMPUTE nodes cannot emit projections.

        COMPUTE nodes are pure transformations that return results only.
        They cannot emit projections - use REDUCER for state management.
        """
        input_envelope_id = uuid4()
        correlation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="test-compute",
                node_kind=EnumNodeKind.COMPUTE,
                result={"data": "value"},
                projections=(
                    "mock_projection",
                ),  # VIOLATION: compute cannot emit projections
            )

        assert "COMPUTE cannot emit projections" in str(exc_info.value)
