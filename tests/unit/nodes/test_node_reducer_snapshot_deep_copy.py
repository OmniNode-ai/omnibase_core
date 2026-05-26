# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeReducer snapshot deep_copy branches and _validate_fsm_snapshot flags.

Covers high-CCN branches in node_reducer.py (CCN 23, 810 lines):
- snapshot_state(deep_copy=True): returns a fully independent copy
- get_state_snapshot(deep_copy=True): returns deep-copied dict
- _validate_fsm_snapshot with validate_required_context=False: skips required key check
- _validate_fsm_snapshot with validate_history_sequence=False: skips dup-history check
- _validate_fsm_snapshot with allow_terminal_state=True via _validate_fsm_snapshot directly
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.fsm import ModelFSMStateSnapshot
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_reducer import NodeReducer

pytestmark = pytest.mark.unit

_V = ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


@pytest.fixture
def fsm_with_required_data() -> ModelFSMSubcontract:
    """FSM with a state that requires specific context keys."""
    return ModelFSMSubcontract(
        state_machine_name="required_data_fsm",
        description="FSM for required_data testing",
        state_machine_version=_V,
        version=_V,
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Initial state",
                version=_V,
                entry_actions=[],
                exit_actions=[],
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                state_type="operational",
                description="Processing state needing context keys",
                version=_V,
                entry_actions=[],
                exit_actions=[],
                required_data=["batch_id", "source"],
            ),
        ],
        transitions=[
            ModelFSMStateTransition(
                transition_name="start",
                from_state="idle",
                to_state="processing",
                trigger="start_event",
                version=_V,
                conditions=[],
                actions=[],
            ),
        ],
        terminal_states=[],
        error_states=[],
        operations=[],
        persistence_enabled=False,
        recovery_enabled=False,
    )


@pytest.fixture
def simple_fsm() -> ModelFSMSubcontract:
    """Minimal two-state FSM for snapshot tests."""
    return ModelFSMSubcontract(
        state_machine_name="snapshot_test_fsm",
        description="Snapshot test FSM",
        state_machine_version=_V,
        version=_V,
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Initial state",
                version=_V,
                entry_actions=[],
                exit_actions=[],
            ),
            ModelFSMStateDefinition(
                state_name="done",
                state_type="terminal",
                description="Terminal state",
                version=_V,
                is_terminal=True,
                is_recoverable=False,
            ),
        ],
        transitions=[
            ModelFSMStateTransition(
                transition_name="finish",
                from_state="idle",
                to_state="done",
                trigger="finish_event",
                version=_V,
                conditions=[],
                actions=[],
            ),
        ],
        terminal_states=["done"],
        error_states=[],
        operations=[],
        persistence_enabled=False,
        recovery_enabled=False,
    )


def _make_node_with_fsm(
    container: ModelONEXContainer,
    fsm: ModelFSMSubcontract,
) -> NodeReducer:  # type: ignore[type-arg]
    node: NodeReducer = NodeReducer.__new__(NodeReducer)
    NodeReducer.__init__(node, container)
    node.fsm_contract = fsm
    node.initialize_fsm_state(fsm, context={})
    return node


class TestSnapshotStateDeepCopy:
    """Tests for snapshot_state(deep_copy=True/False) branches."""

    def test_snapshot_state_deep_copy_true_returns_independent_copy(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        snapshot = node.snapshot_state(deep_copy=True)
        assert snapshot is not None
        assert snapshot is not node._fsm_state

    def test_snapshot_state_deep_copy_false_returns_same_reference(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        snapshot = node.snapshot_state(deep_copy=False)
        assert snapshot is node._fsm_state

    def test_snapshot_state_deep_copy_true_context_is_independent(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        # Inject a mutable context value
        assert node._fsm_state is not None
        node._fsm_state = ModelFSMStateSnapshot(
            current_state="idle",
            context={"key": ["a", "b"]},
            history=[],
        )
        snapshot = node.snapshot_state(deep_copy=True)
        assert snapshot is not None
        # Mutating the deep copy's context does NOT affect the node
        assert isinstance(snapshot.context["key"], list)
        snapshot.context["key"].append("c")  # type: ignore[union-attr]
        assert node._fsm_state.context["key"] == ["a", "b"]

    def test_snapshot_state_deep_copy_preserves_state_values(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        assert node._fsm_state is not None
        node._fsm_state = ModelFSMStateSnapshot(
            current_state="idle",
            context={"x": 42},
            history=["idle"],
        )
        snapshot = node.snapshot_state(deep_copy=True)
        assert snapshot is not None
        assert snapshot.current_state == "idle"
        assert snapshot.context == {"x": 42}
        assert snapshot.history == ["idle"]

    def test_snapshot_state_none_when_not_initialized(
        self, container: ModelONEXContainer
    ) -> None:
        node: NodeReducer = NodeReducer.__new__(NodeReducer)
        NodeReducer.__init__(node, container)
        node.fsm_contract = None
        node._fsm_state = None
        assert node.snapshot_state(deep_copy=True) is None
        assert node.snapshot_state(deep_copy=False) is None


class TestGetStateSnapshotDeepCopy:
    """Tests for get_state_snapshot(deep_copy=True/False) branches."""

    def test_get_state_snapshot_deep_copy_true_returns_dict(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        result = node.get_state_snapshot(deep_copy=True)
        assert isinstance(result, dict)
        assert "current_state" in result

    def test_get_state_snapshot_deep_copy_true_is_independent(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        assert node._fsm_state is not None
        node._fsm_state = ModelFSMStateSnapshot(
            current_state="idle",
            context={"nested": [1, 2, 3]},
            history=[],
        )
        result = node.get_state_snapshot(deep_copy=True)
        assert result is not None
        # Modifying the returned dict does not affect node state
        assert isinstance(result["context"], dict)
        result["context"]["nested"].append(4)  # type: ignore[index,union-attr]
        assert node._fsm_state.context["nested"] == [1, 2, 3]

    def test_get_state_snapshot_deep_copy_false_returns_dict(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        result = node.get_state_snapshot(deep_copy=False)
        assert isinstance(result, dict)

    def test_get_state_snapshot_none_when_not_initialized(
        self, container: ModelONEXContainer
    ) -> None:
        node: NodeReducer = NodeReducer.__new__(NodeReducer)
        NodeReducer.__init__(node, container)
        node._fsm_state = None
        assert node.get_state_snapshot(deep_copy=True) is None
        assert node.get_state_snapshot(deep_copy=False) is None


class TestValidateFSMSnapshotFlags:
    """Tests for _validate_fsm_snapshot optional flag branches."""

    def _make_snapshot(
        self, state: str, context: dict, history: list[str]
    ) -> ModelFSMStateSnapshot:
        return ModelFSMStateSnapshot(
            current_state=state,
            context=context,
            history=history,
        )

    def test_validate_required_context_false_skips_required_key_check(
        self,
        container: ModelONEXContainer,
        fsm_with_required_data: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, fsm_with_required_data)
        # Snapshot for 'processing' which requires batch_id and source — but context is empty
        snapshot = self._make_snapshot("processing", {}, [])
        # Should NOT raise when validate_required_context=False
        node._validate_fsm_snapshot(
            snapshot,
            fsm_with_required_data,
            validate_required_context=False,
        )

    def test_validate_required_context_true_raises_on_missing_keys(
        self,
        container: ModelONEXContainer,
        fsm_with_required_data: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, fsm_with_required_data)
        snapshot = self._make_snapshot("processing", {}, [])
        with pytest.raises(ModelOnexError) as exc_info:
            node._validate_fsm_snapshot(
                snapshot,
                fsm_with_required_data,
                validate_required_context=True,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert (
            "batch_id" in exc_info.value.message or "source" in exc_info.value.message
        )

    def test_validate_history_sequence_false_skips_duplicate_consecutive_check(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        # Duplicate consecutive states — invalid, but skipped
        snapshot = self._make_snapshot("idle", {}, ["idle", "idle"])
        # Should NOT raise when validate_history_sequence=False
        node._validate_fsm_snapshot(
            snapshot,
            simple_fsm,
            validate_history_sequence=False,
        )

    def test_validate_history_sequence_true_raises_on_duplicates(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        snapshot = self._make_snapshot("idle", {}, ["idle", "idle"])
        with pytest.raises(ModelOnexError) as exc_info:
            node._validate_fsm_snapshot(
                snapshot,
                simple_fsm,
                validate_history_sequence=True,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

    def test_allow_terminal_state_true_permits_terminal_restore(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        snapshot = self._make_snapshot("done", {}, [])
        # Should NOT raise with allow_terminal_state=True
        node._validate_fsm_snapshot(
            snapshot,
            simple_fsm,
            allow_terminal_state=True,
        )

    def test_allow_terminal_state_false_raises_on_terminal_restore(
        self,
        container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, simple_fsm)
        snapshot = self._make_snapshot("done", {}, [])
        with pytest.raises(ModelOnexError) as exc_info:
            node._validate_fsm_snapshot(
                snapshot,
                simple_fsm,
                allow_terminal_state=False,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

    def test_all_flags_disabled_accepts_duplicate_history_and_missing_context(
        self,
        container: ModelONEXContainer,
        fsm_with_required_data: ModelFSMSubcontract,
    ) -> None:
        node = _make_node_with_fsm(container, fsm_with_required_data)
        # Both bad: duplicate history and missing required context
        snapshot = self._make_snapshot("processing", {}, ["idle", "idle"])
        node._validate_fsm_snapshot(
            snapshot,
            fsm_with_required_data,
            validate_required_context=False,
            validate_history_sequence=False,
        )
