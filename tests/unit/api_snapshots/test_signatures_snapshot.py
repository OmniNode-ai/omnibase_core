"""
Pre-refactor class signature snapshot tests for omnibase_core node classes.

These tests capture constructor and process method signatures before v0.4.0 refactoring.
If these tests fail due to intentional breaking changes, update them
in the same PR with a migration note in the changelog.

The tests verify:
- Constructor parameter names match expected
- Constructor parameter types match expected (where annotated)
- Required vs optional parameters are correct
- Default values are correct
- Process method signatures are stable (critical for API contracts)
- Process method parameter types and return types are correct

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
    """Signature snapshot tests for NodeEffect.__init__.

    .. versionchanged:: 0.4.0
        NodeEffect refactored to contract-driven implementation.
        Removed on_rollback_failure parameter (now handled via YAML contracts).
        Legacy code-driven implementation available in nodes/legacy/node_effect_legacy.py
    """

    @pytest.mark.unit
    def test_node_effect_init_signature_params(self) -> None:
        """Verify NodeEffect.__init__ parameter names.

        v0.4.0 snapshot: ['self', 'container']

        Note: on_rollback_failure removed in v0.4.0 refactor.
        Rollback handling is now declarative via effect subcontracts.
        """
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.__init__)
        params = list(sig.parameters.keys())

        expected_params = ["self", "container"]
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
    def test_no_node_has_callback_param(self) -> None:
        """Verify no node class has on_rollback_failure callback parameter.

        As of v0.4.0, the legacy code-driven NodeEffectLegacy has been removed.
        The contract-driven NodeEffect (v0.4.0+) does NOT have this parameter.
        Rollback handling is now declarative via effect subcontracts.

        .. versionchanged:: 0.4.0
            Legacy NodeEffectLegacy removed. All nodes now contract-driven.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        # All nodes should NOT have on_rollback_failure (contract-driven)
        all_node_classes = [NodeEffect, NodeCompute, NodeOrchestrator, NodeReducer]
        for node_class in all_node_classes:
            sig = inspect.signature(node_class.__init__)
            assert "on_rollback_failure" not in sig.parameters, (
                f"{node_class.__name__}.__init__ should not have 'on_rollback_failure' "
                "parameter (v0.4.0+: rollback handling is declarative via contracts)"
            )

    @pytest.mark.unit
    def test_signature_param_counts(self) -> None:
        """Verify expected parameter counts for each node class.

        v0.4.0 counts:
        - NodeCompute: 2 params (self, container)
        - NodeEffect: 2 params (self, container) - on_rollback_failure removed in v0.4.0
        - NodeReducer: 2 params (self, container)
        - NodeOrchestrator: 2 params (self, container)
        - NodeCoreBase: 2 params (self, container)
        - NodeBase: 8 params (self, contract_path, node_id, event_bus,
                              container, workflow_id, session_id, kwargs)

        .. versionchanged:: 0.4.0
            NodeEffect reduced from 3 to 2 params (on_rollback_failure removed).
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
            "NodeEffect": 2,  # v0.4.0: on_rollback_failure removed (contract-driven)
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


class TestNodeComputeProcessSignatureSnapshot:
    """Signature snapshot tests for NodeCompute.process method."""

    @pytest.mark.unit
    def test_node_compute_process_signature_params(self) -> None:
        """Verify NodeCompute.process parameter names.

        Pre-refactor snapshot: ['self', 'input_data']
        """
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.process)
        params = list(sig.parameters.keys())

        expected_params = ["self", "input_data"]
        assert params == expected_params, (
            f"NodeCompute.process signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_compute_process_input_required(self) -> None:
        """Verify input_data parameter is required (no default).

        Pre-refactor: input_data has no default value.
        """
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.process)
        input_param = sig.parameters["input_data"]

        assert input_param.default is inspect.Parameter.empty, (
            "NodeCompute.process input_data parameter should be required (no default). "
            f"Got default: {input_param.default}"
        )

    @pytest.mark.unit
    def test_node_compute_process_input_type_annotation(self) -> None:
        """Verify input_data parameter type annotation.

        Pre-refactor: input_data is annotated as ModelComputeInput[T_Input].

        Note: Due to generic type parameters and PEP 695 style generics, we check:
        1. typing.get_origin() for standard generic subscripts
        2. The annotation is the class itself
        3. issubclass() for PEP 695 style generics where typing.get_origin() returns None
           but the annotation is a specialized generic class with ModelComputeInput in its MRO
        """
        import typing

        from omnibase_core.models.compute.model_compute_input import ModelComputeInput
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.process)
        input_param = sig.parameters["input_data"]

        annotation = input_param.annotation
        origin = typing.get_origin(annotation)

        # Accept:
        # 1. Standard generic subscript where origin is ModelComputeInput
        # 2. The class directly (annotation is ModelComputeInput)
        # 3. PEP 695 style generics where annotation is a subclass of ModelComputeInput
        #    (typing.get_origin returns None but issubclass returns True)
        is_valid = (origin is ModelComputeInput) or (annotation is ModelComputeInput)
        if not is_valid:
            # Check for PEP 695 style generics using issubclass
            try:
                is_valid = issubclass(annotation, ModelComputeInput)
            except TypeError:
                # issubclass raises TypeError if annotation is not a class
                is_valid = False

        assert is_valid, (
            f"NodeCompute.process input_data should be annotated as ModelComputeInput[T_Input], "
            f"got {annotation}"
        )

    @pytest.mark.unit
    def test_node_compute_process_return_type_annotation(self) -> None:
        """Verify NodeCompute.process return type annotation.

        Pre-refactor: Returns ModelComputeOutput[T_Output].

        Note: Due to generic type parameters and PEP 695 style generics, we check:
        1. typing.get_origin() for standard generic subscripts
        2. The annotation is the class itself
        3. issubclass() for PEP 695 style generics where typing.get_origin() returns None
           but the annotation is a specialized generic class with ModelComputeOutput in its MRO
        """
        import typing

        from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
        from omnibase_core.nodes import NodeCompute

        sig = inspect.signature(NodeCompute.process)
        return_annotation = sig.return_annotation

        origin = typing.get_origin(return_annotation)

        # Accept:
        # 1. Standard generic subscript where origin is ModelComputeOutput
        # 2. The class directly (return_annotation is ModelComputeOutput)
        # 3. PEP 695 style generics where annotation is a subclass of ModelComputeOutput
        #    (typing.get_origin returns None but issubclass returns True)
        is_valid = (origin is ModelComputeOutput) or (
            return_annotation is ModelComputeOutput
        )
        if not is_valid:
            # Check for PEP 695 style generics using issubclass
            try:
                is_valid = issubclass(return_annotation, ModelComputeOutput)
            except TypeError:
                # issubclass raises TypeError if return_annotation is not a class
                is_valid = False

        assert is_valid, (
            f"NodeCompute.process should return ModelComputeOutput[T_Output], "
            f"got {return_annotation}"
        )

    @pytest.mark.unit
    def test_node_compute_process_is_async(self) -> None:
        """Verify NodeCompute.process is an async method.

        Pre-refactor: process is defined as async def.
        """
        from omnibase_core.nodes import NodeCompute

        assert inspect.iscoroutinefunction(NodeCompute.process), (
            "NodeCompute.process must be an async method (coroutine function)"
        )


class TestNodeEffectProcessSignatureSnapshot:
    """Signature snapshot tests for NodeEffect.process method."""

    @pytest.mark.unit
    def test_node_effect_process_signature_params(self) -> None:
        """Verify NodeEffect.process parameter names.

        Pre-refactor snapshot: ['self', 'input_data']
        """
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.process)
        params = list(sig.parameters.keys())

        expected_params = ["self", "input_data"]
        assert params == expected_params, (
            f"NodeEffect.process signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_effect_process_input_required(self) -> None:
        """Verify input_data parameter is required (no default).

        Pre-refactor: input_data has no default value.
        """
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.process)
        input_param = sig.parameters["input_data"]

        assert input_param.default is inspect.Parameter.empty, (
            "NodeEffect.process input_data parameter should be required (no default). "
            f"Got default: {input_param.default}"
        )

    @pytest.mark.unit
    def test_node_effect_process_input_type_annotation(self) -> None:
        """Verify input_data parameter type annotation.

        Pre-refactor: input_data is annotated as ModelEffectInput.
        """
        from omnibase_core.models.effect.model_effect_input import ModelEffectInput
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.process)
        input_param = sig.parameters["input_data"]

        assert input_param.annotation is ModelEffectInput, (
            f"NodeEffect.process input_data should be annotated as ModelEffectInput, "
            f"got {input_param.annotation}"
        )

    @pytest.mark.unit
    def test_node_effect_process_return_type_annotation(self) -> None:
        """Verify NodeEffect.process return type annotation.

        Pre-refactor: Returns ModelEffectOutput.
        """
        from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
        from omnibase_core.nodes import NodeEffect

        sig = inspect.signature(NodeEffect.process)

        assert sig.return_annotation is ModelEffectOutput, (
            f"NodeEffect.process should return ModelEffectOutput, "
            f"got {sig.return_annotation}"
        )

    @pytest.mark.unit
    def test_node_effect_process_is_async(self) -> None:
        """Verify NodeEffect.process is an async method.

        Pre-refactor: process is defined as async def.
        """
        from omnibase_core.nodes import NodeEffect

        assert inspect.iscoroutinefunction(NodeEffect.process), (
            "NodeEffect.process must be an async method (coroutine function)"
        )


class TestNodeReducerProcessSignatureSnapshot:
    """Signature snapshot tests for NodeReducer.process method."""

    @pytest.mark.unit
    def test_node_reducer_process_signature_params(self) -> None:
        """Verify NodeReducer.process parameter names.

        Pre-refactor snapshot: ['self', 'input_data']
        """
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.process)
        params = list(sig.parameters.keys())

        expected_params = ["self", "input_data"]
        assert params == expected_params, (
            f"NodeReducer.process signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_reducer_process_input_required(self) -> None:
        """Verify input_data parameter is required (no default).

        Pre-refactor: input_data has no default value.
        """
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.process)
        input_param = sig.parameters["input_data"]

        assert input_param.default is inspect.Parameter.empty, (
            "NodeReducer.process input_data parameter should be required (no default). "
            f"Got default: {input_param.default}"
        )

    @pytest.mark.unit
    def test_node_reducer_process_input_type_annotation(self) -> None:
        """Verify input_data parameter type annotation.

        Pre-refactor: input_data is annotated as ModelReducerInput[T_Input].

        Note: Due to generic type parameters and PEP 695 style generics, we check:
        1. typing.get_origin() for standard generic subscripts
        2. The annotation is the class itself
        3. issubclass() for PEP 695 style generics where typing.get_origin() returns None
           but the annotation is a specialized generic class with ModelReducerInput in its MRO
        """
        import typing

        from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.process)
        input_param = sig.parameters["input_data"]

        annotation = input_param.annotation
        origin = typing.get_origin(annotation)

        # Accept:
        # 1. Standard generic subscript where origin is ModelReducerInput
        # 2. The class directly (annotation is ModelReducerInput)
        # 3. PEP 695 style generics where annotation is a subclass of ModelReducerInput
        #    (typing.get_origin returns None but issubclass returns True)
        is_valid = (origin is ModelReducerInput) or (annotation is ModelReducerInput)
        if not is_valid:
            # Check for PEP 695 style generics using issubclass
            try:
                is_valid = issubclass(annotation, ModelReducerInput)
            except TypeError:
                # issubclass raises TypeError if annotation is not a class
                is_valid = False

        assert is_valid, (
            f"NodeReducer.process input_data should be annotated as ModelReducerInput[T_Input], "
            f"got {annotation}"
        )

    @pytest.mark.unit
    def test_node_reducer_process_return_type_annotation(self) -> None:
        """Verify NodeReducer.process return type annotation.

        Pre-refactor: Returns ModelReducerOutput[T_Output].

        Note: Due to generic type parameters and PEP 695 style generics, we check:
        1. typing.get_origin() for standard generic subscripts
        2. The annotation is the class itself
        3. issubclass() for PEP 695 style generics where typing.get_origin() returns None
           but the annotation is a specialized generic class with ModelReducerOutput in its MRO
        """
        import typing

        from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
        from omnibase_core.nodes import NodeReducer

        sig = inspect.signature(NodeReducer.process)
        return_annotation = sig.return_annotation

        origin = typing.get_origin(return_annotation)

        # Accept:
        # 1. Standard generic subscript where origin is ModelReducerOutput
        # 2. The class directly (return_annotation is ModelReducerOutput)
        # 3. PEP 695 style generics where annotation is a subclass of ModelReducerOutput
        #    (typing.get_origin returns None but issubclass returns True)
        is_valid = (origin is ModelReducerOutput) or (
            return_annotation is ModelReducerOutput
        )
        if not is_valid:
            # Check for PEP 695 style generics using issubclass
            try:
                is_valid = issubclass(return_annotation, ModelReducerOutput)
            except TypeError:
                # issubclass raises TypeError if return_annotation is not a class
                is_valid = False

        assert is_valid, (
            f"NodeReducer.process should return ModelReducerOutput[T_Output], "
            f"got {return_annotation}"
        )

    @pytest.mark.unit
    def test_node_reducer_process_is_async(self) -> None:
        """Verify NodeReducer.process is an async method.

        Pre-refactor: process is defined as async def.
        """
        from omnibase_core.nodes import NodeReducer

        assert inspect.iscoroutinefunction(NodeReducer.process), (
            "NodeReducer.process must be an async method (coroutine function)"
        )


class TestNodeOrchestratorProcessSignatureSnapshot:
    """Signature snapshot tests for NodeOrchestrator.process method."""

    @pytest.mark.unit
    def test_node_orchestrator_process_signature_params(self) -> None:
        """Verify NodeOrchestrator.process parameter names.

        Pre-refactor snapshot: ['self', 'input_data']
        """
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.process)
        params = list(sig.parameters.keys())

        expected_params = ["self", "input_data"]
        assert params == expected_params, (
            f"NodeOrchestrator.process signature changed. "
            f"Expected params: {expected_params}, Got: {params}"
        )

    @pytest.mark.unit
    def test_node_orchestrator_process_input_required(self) -> None:
        """Verify input_data parameter is required (no default).

        Pre-refactor: input_data has no default value.
        """
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.process)
        input_param = sig.parameters["input_data"]

        assert input_param.default is inspect.Parameter.empty, (
            "NodeOrchestrator.process input_data parameter should be required (no default). "
            f"Got default: {input_param.default}"
        )

    @pytest.mark.unit
    def test_node_orchestrator_process_input_type_annotation(self) -> None:
        """Verify input_data parameter type annotation.

        Pre-refactor: input_data is annotated as ModelOrchestratorInput.
        """
        from omnibase_core.models.orchestrator.model_orchestrator_input import (
            ModelOrchestratorInput,
        )
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.process)
        input_param = sig.parameters["input_data"]

        assert input_param.annotation is ModelOrchestratorInput, (
            f"NodeOrchestrator.process input_data should be annotated as ModelOrchestratorInput, "
            f"got {input_param.annotation}"
        )

    @pytest.mark.unit
    def test_node_orchestrator_process_return_type_annotation(self) -> None:
        """Verify NodeOrchestrator.process return type annotation.

        Pre-refactor: Returns ModelOrchestratorOutput.
        """
        from omnibase_core.models.orchestrator import ModelOrchestratorOutput
        from omnibase_core.nodes import NodeOrchestrator

        sig = inspect.signature(NodeOrchestrator.process)

        assert sig.return_annotation is ModelOrchestratorOutput, (
            f"NodeOrchestrator.process should return ModelOrchestratorOutput, "
            f"got {sig.return_annotation}"
        )

    @pytest.mark.unit
    def test_node_orchestrator_process_is_async(self) -> None:
        """Verify NodeOrchestrator.process is an async method.

        Pre-refactor: process is defined as async def.
        """
        from omnibase_core.nodes import NodeOrchestrator

        assert inspect.iscoroutinefunction(NodeOrchestrator.process), (
            "NodeOrchestrator.process must be an async method (coroutine function)"
        )


class TestProcessSignatureComprehensiveSummary:
    """Summary tests for all node process method signatures.

    These tests provide a quick overview of all node process signatures
    for verification during refactoring.
    """

    @pytest.mark.unit
    def test_all_four_node_classes_have_process_method(self) -> None:
        """Verify all 4-node architecture classes have a process method.

        This is the core processing interface for all nodes.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            assert hasattr(node_class, "process"), (
                f"{node_class.__name__} must have 'process' method"
            )
            assert callable(node_class.process), (
                f"{node_class.__name__}.process must be callable"
            )

    @pytest.mark.unit
    def test_all_process_methods_are_async(self) -> None:
        """Verify all 4-node process methods are async.

        Pattern: async def process(self, input_data: ...) -> ...
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            assert inspect.iscoroutinefunction(node_class.process), (
                f"{node_class.__name__}.process must be async (coroutine function)"
            )

    @pytest.mark.unit
    def test_all_process_methods_have_input_data_param(self) -> None:
        """Verify all 4-node process methods have input_data parameter.

        Pattern: async def process(self, input_data: ...) -> ...
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            sig = inspect.signature(node_class.process)
            assert "input_data" in sig.parameters, (
                f"{node_class.__name__}.process must have 'input_data' parameter"
            )

    @pytest.mark.unit
    def test_process_signature_param_counts(self) -> None:
        """Verify expected parameter counts for each node process method.

        Pre-refactor counts (all have 2 params: self, input_data):
        - NodeCompute.process: 2 params
        - NodeEffect.process: 2 params
        - NodeReducer.process: 2 params
        - NodeOrchestrator.process: 2 params
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        expected_count = 2  # self and input_data

        node_classes = {
            "NodeCompute": NodeCompute,
            "NodeEffect": NodeEffect,
            "NodeReducer": NodeReducer,
            "NodeOrchestrator": NodeOrchestrator,
        }

        for name, cls in node_classes.items():
            sig = inspect.signature(cls.process)
            actual_count = len(sig.parameters)
            assert actual_count == expected_count, (
                f"{name}.process parameter count changed. "
                f"Expected {expected_count}, got {actual_count}. "
                f"Params: {list(sig.parameters.keys())}"
            )

    @pytest.mark.unit
    def test_process_methods_have_return_annotations(self) -> None:
        """Verify all 4-node process methods have return type annotations.

        All process methods should have explicit return type annotations
        for code generation and type safety.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            sig = inspect.signature(node_class.process)
            assert sig.return_annotation is not inspect.Parameter.empty, (
                f"{node_class.__name__}.process must have return type annotation"
            )

    @pytest.mark.unit
    def test_process_input_params_have_type_annotations(self) -> None:
        """Verify all 4-node process input_data parameters have type annotations.

        All input_data parameters should have explicit type annotations
        for code generation and type safety.
        """
        from omnibase_core.nodes import (
            NodeCompute,
            NodeEffect,
            NodeOrchestrator,
            NodeReducer,
        )

        node_classes = [NodeCompute, NodeEffect, NodeOrchestrator, NodeReducer]

        for node_class in node_classes:
            sig = inspect.signature(node_class.process)
            input_param = sig.parameters["input_data"]
            assert input_param.annotation is not inspect.Parameter.empty, (
                f"{node_class.__name__}.process input_data must have type annotation"
            )
