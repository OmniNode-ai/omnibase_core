"""
Pre-refactor class signature snapshot tests for omnibase_core node classes.

These tests capture constructor signatures before v0.4.0 refactoring.
If these tests fail due to intentional breaking changes, update them
in the same PR with a migration note in the changelog.

The tests verify:
- Constructor parameter names match expected
- Constructor parameter types match expected (where annotated)
- Required vs optional parameters are correct
- Default values are correct

VERSION: 1.0.0 (API stability guarantee per node modules)
STABILITY: Node signatures are frozen for code generation.
           Breaking changes require major version bump.

Captured: 2025-12-03 (OMN-149)
"""

import inspect
from pathlib import Path

import pytest


class TestNodeComputeSignatureSnapshot:
    """Signature snapshot tests for NodeCompute.__init__."""

    @pytest.mark.unit
    def test_node_compute_init_signature_params(self) -> None:
        """Verify NodeCompute.__init__ parameter names.

        Pre-refactor snapshot: ['self', 'container']
        """
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.__init__)
        params = list(sig.parameters.keys())

        expected_params = ["self", "container"]
        assert params == expected_params, (
            f"NodeCompute.__init__ signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_compute_init_container_required(self) -> None:
        """Verify container parameter is required (no default).

        Pre-refactor: container has no default value.
        """
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.__init__)
        container_param = sig.parameters["container"]

        assert container_param.default is inspect.Parameter.empty, (
            "NodeCompute.__init__ container parameter should be required (no default). "
            f"Got default: {container_param.default}"
        )

    @pytest.mark.unit
    def test_node_compute_init_return_type(self) -> None:
        """Verify NodeCompute.__init__ return type annotation is None."""
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.__init__)

        assert sig.return_annotation is None or sig.return_annotation is type(None), (
            f"NodeCompute.__init__ should return None, got {sig.return_annotation}"
        )

    @pytest.mark.unit
    def test_node_compute_init_container_type_annotation(self) -> None:
        """Verify container parameter type annotation.

        Pre-refactor: container is annotated as ModelONEXContainer.
        """
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.__init__)
        container_param = sig.parameters["container"]

        # Check annotation matches expected type
        assert container_param.annotation is ModelONEXContainer, (
            f"NodeCompute.__init__ container should be annotated as ModelONEXContainer, "
            f"got {container_param.annotation}"
        )


class TestNodeEffectSignatureSnapshot:
    """Signature snapshot tests for NodeEffect.__init__."""

    @pytest.mark.unit
    def test_node_effect_init_signature_params(self) -> None:
        """Verify NodeEffect.__init__ parameter names.

        Pre-refactor snapshot: ['self', 'container', 'on_rollback_failure']
        """
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.__init__)
        params = list(sig.parameters.keys())

        expected_params = ["self", "container", "on_rollback_failure"]
        assert params == expected_params, (
            f"NodeEffect.__init__ signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_effect_init_container_required(self) -> None:
        """Verify container parameter is required (no default).

        Pre-refactor: container has no default value.
        """
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.__init__)
        container_param = sig.parameters["container"]

        assert container_param.default is inspect.Parameter.empty, (
            "NodeEffect.__init__ container parameter should be required (no default). "
            f"Got default: {container_param.default}"
        )

    @pytest.mark.unit
    def test_node_effect_init_on_rollback_failure_optional(self) -> None:
        """Verify on_rollback_failure parameter is optional with None default.

        Pre-refactor: on_rollback_failure defaults to None.
        """
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.__init__)
        callback_param = sig.parameters["on_rollback_failure"]

        assert callback_param.default is None, (
            "NodeEffect.__init__ on_rollback_failure should default to None. "
            f"Got default: {callback_param.default}"
        )

    @pytest.mark.unit
    def test_node_effect_init_return_type(self) -> None:
        """Verify NodeEffect.__init__ return type annotation is None."""
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.__init__)

        assert sig.return_annotation is None or sig.return_annotation is type(None), (
            f"NodeEffect.__init__ should return None, got {sig.return_annotation}"
        )

    @pytest.mark.unit
    def test_node_effect_init_container_type_annotation(self) -> None:
        """Verify container parameter type annotation.

        Pre-refactor: container is annotated as ModelONEXContainer.
        """
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.__init__)
        container_param = sig.parameters["container"]

        assert container_param.annotation is ModelONEXContainer, (
            f"NodeEffect.__init__ container should be annotated as ModelONEXContainer, "
            f"got {container_param.annotation}"
        )


class TestNodeReducerSignatureSnapshot:
    """Signature snapshot tests for NodeReducer.__init__."""

    @pytest.mark.unit
    def test_node_reducer_init_signature_params(self) -> None:
        """Verify NodeReducer.__init__ parameter names.

        Pre-refactor snapshot: ['self', 'container']
        """
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.__init__)
        params = list(sig.parameters.keys())

        expected_params = ["self", "container"]
        assert params == expected_params, (
            f"NodeReducer.__init__ signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_reducer_init_container_required(self) -> None:
        """Verify container parameter is required (no default).

        Pre-refactor: container has no default value.
        """
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.__init__)
        container_param = sig.parameters["container"]

        assert container_param.default is inspect.Parameter.empty, (
            "NodeReducer.__init__ container parameter should be required (no default). "
            f"Got default: {container_param.default}"
        )

    @pytest.mark.unit
    def test_node_reducer_init_return_type(self) -> None:
        """Verify NodeReducer.__init__ return type annotation is None."""
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.__init__)

        assert sig.return_annotation is None or sig.return_annotation is type(None), (
            f"NodeReducer.__init__ should return None, got {sig.return_annotation}"
        )

    @pytest.mark.unit
    def test_node_reducer_init_container_type_annotation(self) -> None:
        """Verify container parameter type annotation.

        Pre-refactor: container is annotated as ModelONEXContainer.
        """
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.__init__)
        container_param = sig.parameters["container"]

        assert container_param.annotation is ModelONEXContainer, (
            f"NodeReducer.__init__ container should be annotated as ModelONEXContainer, "
            f"got {container_param.annotation}"
        )


class TestNodeOrchestratorSignatureSnapshot:
    """Signature snapshot tests for NodeOrchestrator.__init__."""

    @pytest.mark.unit
    def test_node_orchestrator_init_signature_params(self) -> None:
        """Verify NodeOrchestrator.__init__ parameter names.

        Pre-refactor snapshot: ['self', 'container']
        """
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.__init__)
        params = list(sig.parameters.keys())

        expected_params = ["self", "container"]
        assert params == expected_params, (
            f"NodeOrchestrator.__init__ signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_orchestrator_init_container_required(self) -> None:
        """Verify container parameter is required (no default).

        Pre-refactor: container has no default value.
        """
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.__init__)
        container_param = sig.parameters["container"]

        assert container_param.default is inspect.Parameter.empty, (
            "NodeOrchestrator.__init__ container parameter should be required (no default). "
            f"Got default: {container_param.default}"
        )

    @pytest.mark.unit
    def test_node_orchestrator_init_return_type(self) -> None:
        """Verify NodeOrchestrator.__init__ return type annotation is None."""
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.__init__)

        assert sig.return_annotation is None or sig.return_annotation is type(None), (
            f"NodeOrchestrator.__init__ should return None, got {sig.return_annotation}"
        )

    @pytest.mark.unit
    def test_node_orchestrator_init_container_type_annotation(self) -> None:
        """Verify container parameter type annotation.

        Pre-refactor: container is annotated as ModelONEXContainer.
        """
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.__init__)
        container_param = sig.parameters["container"]

        assert container_param.annotation is ModelONEXContainer, (
            f"NodeOrchestrator.__init__ container should be annotated as ModelONEXContainer, "
            f"got {container_param.annotation}"
        )


class TestNodeCoreBaseSignatureSnapshot:
    """Signature snapshot tests for NodeCoreBase.__init__."""

    @pytest.mark.unit
    def test_node_core_base_init_signature_params(self) -> None:
        """Verify NodeCoreBase.__init__ parameter names.

        Pre-refactor snapshot: ['self', 'container']
        """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        sig = inspect.signature(NodeCoreBase.__init__)
        params = list(sig.parameters.keys())

        expected_params = ["self", "container"]
        assert params == expected_params, (
            f"NodeCoreBase.__init__ signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_core_base_init_container_required(self) -> None:
        """Verify container parameter is required (no default).

        Pre-refactor: container has no default value.
        """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        sig = inspect.signature(NodeCoreBase.__init__)
        container_param = sig.parameters["container"]

        assert container_param.default is inspect.Parameter.empty, (
            "NodeCoreBase.__init__ container parameter should be required (no default). "
            f"Got default: {container_param.default}"
        )

    @pytest.mark.unit
    def test_node_core_base_init_return_type(self) -> None:
        """Verify NodeCoreBase.__init__ return type annotation is None.

        Note: Due to PEP 563 (from __future__ import annotations), type annotations
        are stored as strings. We check for both the actual type and string representation.
        """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        sig = inspect.signature(NodeCoreBase.__init__)

        # Handle both actual type and stringified annotation (PEP 563)
        valid_none_annotations = (None, type(None), "None")
        assert sig.return_annotation in valid_none_annotations, (
            f"NodeCoreBase.__init__ should return None, got {sig.return_annotation}"
        )


class TestNodeBaseSignatureSnapshot:
    """Signature snapshot tests for NodeBase.__init__.

    NodeBase has a more complex signature with multiple optional parameters.
    """

    @pytest.mark.unit
    def test_node_base_init_signature_params(self) -> None:
        """Verify NodeBase.__init__ parameter names.

        Pre-refactor snapshot: ['self', 'contract_path', 'node_id', 'event_bus',
                                'container', 'workflow_id', 'session_id', 'kwargs']
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        params = list(sig.parameters.keys())

        expected_params = [
            "self",
            "contract_path",
            "node_id",
            "event_bus",
            "container",
            "workflow_id",
            "session_id",
            "kwargs",
        ]
        assert params == expected_params, (
            f"NodeBase.__init__ signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_base_init_contract_path_required(self) -> None:
        """Verify contract_path parameter is required (no default).

        Pre-refactor: contract_path has no default value.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        contract_path_param = sig.parameters["contract_path"]

        assert contract_path_param.default is inspect.Parameter.empty, (
            "NodeBase.__init__ contract_path parameter should be required (no default). "
            f"Got default: {contract_path_param.default}"
        )

    @pytest.mark.unit
    def test_node_base_init_node_id_optional(self) -> None:
        """Verify node_id parameter is optional with None default.

        Pre-refactor: node_id defaults to None.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        node_id_param = sig.parameters["node_id"]

        assert node_id_param.default is None, (
            "NodeBase.__init__ node_id should default to None. "
            f"Got default: {node_id_param.default}"
        )

    @pytest.mark.unit
    def test_node_base_init_event_bus_optional(self) -> None:
        """Verify event_bus parameter is optional with None default.

        Pre-refactor: event_bus defaults to None.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        event_bus_param = sig.parameters["event_bus"]

        assert event_bus_param.default is None, (
            "NodeBase.__init__ event_bus should default to None. "
            f"Got default: {event_bus_param.default}"
        )

    @pytest.mark.unit
    def test_node_base_init_container_optional(self) -> None:
        """Verify container parameter is optional with None default.

        Pre-refactor: container defaults to None (NodeBase creates one if not provided).
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        container_param = sig.parameters["container"]

        assert container_param.default is None, (
            "NodeBase.__init__ container should default to None. "
            f"Got default: {container_param.default}"
        )

    @pytest.mark.unit
    def test_node_base_init_workflow_id_optional(self) -> None:
        """Verify workflow_id parameter is optional with None default.

        Pre-refactor: workflow_id defaults to None.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        workflow_id_param = sig.parameters["workflow_id"]

        assert workflow_id_param.default is None, (
            "NodeBase.__init__ workflow_id should default to None. "
            f"Got default: {workflow_id_param.default}"
        )

    @pytest.mark.unit
    def test_node_base_init_session_id_optional(self) -> None:
        """Verify session_id parameter is optional with None default.

        Pre-refactor: session_id defaults to None.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        session_id_param = sig.parameters["session_id"]

        assert session_id_param.default is None, (
            "NodeBase.__init__ session_id should default to None. "
            f"Got default: {session_id_param.default}"
        )

    @pytest.mark.unit
    def test_node_base_init_kwargs_variadic(self) -> None:
        """Verify kwargs parameter is VAR_KEYWORD type (**kwargs).

        Pre-refactor: **kwargs is accepted for additional parameters.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        kwargs_param = sig.parameters["kwargs"]

        assert kwargs_param.kind == inspect.Parameter.VAR_KEYWORD, (
            "NodeBase.__init__ kwargs should be VAR_KEYWORD (**kwargs). "
            f"Got kind: {kwargs_param.kind}"
        )

    @pytest.mark.unit
    def test_node_base_init_return_type(self) -> None:
        """Verify NodeBase.__init__ return type annotation is None.

        Note: Due to PEP 563 (from __future__ import annotations), type annotations
        are stored as strings. We check for both the actual type and string representation.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)

        # Handle both actual type and stringified annotation (PEP 563)
        valid_none_annotations = (None, type(None), "None")
        assert sig.return_annotation in valid_none_annotations, (
            f"NodeBase.__init__ should return None, got {sig.return_annotation}"
        )

    @pytest.mark.unit
    def test_node_base_init_contract_path_type_annotation(self) -> None:
        """Verify contract_path parameter type annotation.

        Pre-refactor: contract_path is annotated as Path.

        Note: Due to PEP 563 (from __future__ import annotations), type annotations
        are stored as strings. We check for both the actual type and string representation.
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        sig = inspect.signature(NodeBase.__init__)
        contract_path_param = sig.parameters["contract_path"]

        # Handle both actual type and stringified annotation (PEP 563)
        valid_path_annotations = (Path, "Path")
        assert contract_path_param.annotation in valid_path_annotations, (
            f"NodeBase.__init__ contract_path should be annotated as Path, "
            f"got {contract_path_param.annotation}"
        )


class TestSignatureComprehensiveSummary:
    """Summary tests for all node signatures.

    These tests provide a quick overview of all node signatures
    for verification during refactoring.
    """

    @pytest.mark.unit
    def test_all_four_node_architecture_classes_have_container_param(self) -> None:
        """Verify all 4-node architecture classes accept container parameter.

        This is the unified interface for dependency injection across all nodes.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            sig = inspect.signature(node_class.__init__)
            assert "container" in sig.parameters, (
                f"{node_class.__name__}.__init__ must have 'container' parameter"
            )

    @pytest.mark.unit
    def test_four_node_container_param_first_after_self(self) -> None:
        """Verify container is the first parameter after self for 4-node classes.

        Pattern: __init__(self, container: ModelONEXContainer, ...)
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            sig = inspect.signature(node_class.__init__)
            params = list(sig.parameters.keys())

            assert len(params) >= 2, (
                f"{node_class.__name__}.__init__ must have at least self and container"
            )
            assert params[0] == "self", (
                f"{node_class.__name__}.__init__ first param must be 'self'"
            )
            assert params[1] == "container", (
                f"{node_class.__name__}.__init__ second param must be 'container', "
                f"got '{params[1]}'"
            )

    @pytest.mark.unit
    def test_node_effect_is_only_node_with_callback_param(self) -> None:
        """Verify only NodeEffect has on_rollback_failure callback parameter.

        NodeEffect is unique in accepting an optional callback for rollback failures.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        # NodeEffect should have on_rollback_failure
        effect_sig = inspect.signature(NodeEffect.__init__)
        assert "on_rollback_failure" in effect_sig.parameters, (
            "NodeEffect.__init__ must have 'on_rollback_failure' parameter"
        )

        # Other nodes should NOT have it
        other_classes = [NodeCompute, NodeOrchestrator, NodeReducer]
        for node_class in other_classes:
            sig = inspect.signature(node_class.__init__)
            assert "on_rollback_failure" not in sig.parameters, (
                f"{node_class.__name__}.__init__ should not have 'on_rollback_failure' "
                "parameter (only NodeEffect should)"
            )

    @pytest.mark.unit
    def test_signature_param_counts(self) -> None:
        """Verify expected parameter counts for each node class.

        Pre-refactor counts:
        - NodeCompute: 2 params (self, container)
        - NodeEffect: 3 params (self, container, on_rollback_failure)
        - NodeReducer: 2 params (self, container)
        - NodeOrchestrator: 2 params (self, container)
        - NodeCoreBase: 2 params (self, container)
        - NodeBase: 8 params (self, contract_path, node_id, event_bus,
                              container, workflow_id, session_id, kwargs)
        """
        from omnibase_core.infrastructure.node_base import NodeBase
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        expected_counts = {
            "NodeCompute": 2,
            "NodeEffect": 3,
            "NodeReducer": 2,
            "NodeOrchestrator": 2,
            "NodeCoreBase": 2,
            "NodeBase": 8,
        }

        classes = {
            "NodeCompute": NodeCompute,
            "NodeEffect": NodeEffect,
            "NodeReducer": NodeReducer,
            "NodeOrchestrator": NodeOrchestrator,
            "NodeCoreBase": NodeCoreBase,
            "NodeBase": NodeBase,
        }

        for name, cls in classes.items():
            sig = inspect.signature(cls.__init__)
            actual_count = len(sig.parameters)
            expected_count = expected_counts[name]
            assert actual_count == expected_count, (
                f"{name}.__init__ parameter count changed. "
                f"Expected {expected_count}, got {actual_count}. "
                f"Params: {list(sig.parameters.keys())}"
            )
