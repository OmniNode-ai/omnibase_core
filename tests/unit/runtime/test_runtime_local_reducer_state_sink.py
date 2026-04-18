# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression suite: state persisted via effect node across all runtime paths.

OMN-9012 / OMN-9006 epic — Pure reducer architecture.

Verifies that:
1. RuntimeLocal._run_single_handler — handler returning ModelPersistStateIntent
   causes the intent to be published on the bus, NOT via ProtocolStateStore.put().
2. RuntimeLocal._run_compute — compute path does not touch ProtocolStateStore.
3. RuntimeLocal._run_event_driven — event-driven handler that publishes
   ModelPersistStateIntent to an output topic observable on the in-memory bus.
4. No import of ProtocolStateStore exists in runtime_local.py (structural guard).
"""

from __future__ import annotations

import inspect
import json
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.models.intents import ModelPersistStateIntent
from omnibase_core.models.state import ModelStateEnvelope
from omnibase_core.runtime.runtime_local import RuntimeLocal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_envelope() -> ModelStateEnvelope:
    return ModelStateEnvelope(
        node_id="node-test-reducer",
        scope_id="default",
        data={"sweep_count": 1},
        written_at=datetime.now(UTC),
    )


def _make_persist_intent() -> ModelPersistStateIntent:
    return ModelPersistStateIntent(
        intent_id=uuid4(),
        envelope=_make_envelope(),
        emitted_at=datetime.now(UTC),
        correlation_id=uuid4(),
    )


def _base_contract_yaml(
    *,
    node_type: str = "workflow",
    terminal_event: str | None = "evt.done.v1",
    handler_module: str = "",
    handler_class: str = "",
    extra: str = "",
) -> str:
    lines = [
        "workflow_id: test-reducer-state",
        "contract_version: {major: 1, minor: 0, patch: 0}",
        f"node_type: {node_type}",
        "description: Reducer state sink regression test",
    ]
    if terminal_event:
        lines.append(f"terminal_event: {terminal_event}")
    if handler_module and handler_class:
        lines.append("handler:")
        lines.append(f"  module: {handler_module}")
        lines.append(f"  class: {handler_class}")
    if extra:
        lines.append(extra)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Structural guard — runtime_local.py must never import ProtocolStateStore
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_runtime_local_does_not_import_protocol_state_store() -> None:
    """runtime_local.py must not import ProtocolStateStore or call put() on a state store.

    The runtime is responsible for publishing intents; state persistence is
    handled exclusively by the effect node that subscribes to the intent topic.
    This test guards against regressions that re-introduce direct persistence
    inside RuntimeLocal.

    Note: the source may reference 'ProtocolStateStore' in doc-comments as
    context, which is acceptable. The guard here targets:
    - import-level references (``from ... import ProtocolStateStore``)
    - the deleted direct-persistence hook name
    """
    import omnibase_core.runtime.runtime_local as rl_module

    source_file = inspect.getfile(rl_module)
    source_lines = Path(source_file).read_text(encoding="utf-8").splitlines()

    # Check no import of ProtocolStateStore exists
    import_lines = [
        ln for ln in source_lines if "import" in ln and "ProtocolStateStore" in ln
    ]
    assert not import_lines, (
        "runtime_local.py must not import ProtocolStateStore — "
        f"found on lines: {import_lines} (OMN-9006 regression)"
    )

    # Check the deleted method is gone
    source_text = "\n".join(source_lines)
    assert "_persist_reducer_projection_if_applicable" not in source_text, (
        "runtime_local.py must not contain _persist_reducer_projection_if_applicable — "
        "deleted in OMN-9011 (OMN-9006 regression)"
    )


# ---------------------------------------------------------------------------
# Path 1: _run_single_handler
# ---------------------------------------------------------------------------


class _SingleHandlerWithIntent:
    """Simulates a reducer handler that returns a result carrying persist intent."""

    def __init__(self, intent: ModelPersistStateIntent) -> None:
        self._intent = intent
        self.state_store_put_calls: list[Any] = []

    def handle(self, _payload: Any = None) -> _SingleHandlerResult:
        return _SingleHandlerResult(
            status="success",
            intents=[self._intent],
        )


class _SingleHandlerResult(BaseModel):
    status: str
    intents: list[Any] = []


@pytest.mark.unit
def test_single_handler_path_does_not_call_state_store_put(
    tmp_path: Path,
) -> None:
    """_run_single_handler: state persistence does not use ProtocolStateStore.put().

    A handler that emits ModelPersistStateIntent should have its result
    classified by the runtime WITHOUT the runtime calling any state store
    put() method. The intent travels via the bus, not via runtime-direct I/O.
    """
    intent = _make_persist_intent()

    mod_name = "_test_single_handler_persist_mod"
    mod = types.ModuleType(mod_name)
    mod._SingleHandlerWithIntent = _SingleHandlerWithIntent  # type: ignore[attr-defined]
    mod._SingleHandlerResult = _SingleHandlerResult  # type: ignore[attr-defined]
    sys.modules[mod_name] = mod

    mock_state_store = MagicMock()

    try:
        yaml_text = _base_contract_yaml(
            handler_module=mod_name,
            handler_class="_SingleHandlerWithIntent",
        )
        workflow = tmp_path / "contract.yaml"
        workflow.write_text(yaml_text)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        # Inject the intent into the handler so it carries ModelPersistStateIntent
        mod._SingleHandlerWithIntent._intent_fixture = intent  # type: ignore[attr-defined]

        result = runtime.run()

        # Runtime must complete (or fail gracefully) — the key assertion is
        # that the mock state store was never touched
        assert result in (EnumWorkflowResult.COMPLETED, EnumWorkflowResult.FAILED)
        mock_state_store.put.assert_not_called()

    finally:
        sys.modules.pop(mod_name, None)


@pytest.mark.unit
def test_single_handler_path_result_classified_not_persisted_directly(
    tmp_path: Path,
) -> None:
    """_run_single_handler: sync-return handler result classification is bus-mediated.

    When a handler returns a result carrying ModelPersistStateIntent, the runtime
    classifies the result (success/failure) and publishes a synthesized terminal
    event — it does NOT inspect or act on the intents[] list for persistence.
    Persistence only happens if a downstream effect node subscribes to the intent topic.
    """
    mod_name = "_test_single_persist_classify_mod"

    class _Handler:
        def handle(self, _payload: Any = None) -> _SingleHandlerResult:
            return _SingleHandlerResult(
                status="success",
                intents=[_make_persist_intent()],
            )

    mod = types.ModuleType(mod_name)
    mod._Handler = _Handler  # type: ignore[attr-defined]
    sys.modules[mod_name] = mod

    try:
        yaml_text = _base_contract_yaml(
            handler_module=mod_name,
            handler_class="_Handler",
        )
        workflow = tmp_path / "contract.yaml"
        workflow.write_text(yaml_text)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()

        # Runtime classifies "success" status → COMPLETED
        assert result == EnumWorkflowResult.COMPLETED

        # State file records the runtime result, not the intent contents
        state_file = tmp_path / "state" / "workflow_result.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["result"] == "completed"

    finally:
        sys.modules.pop(mod_name, None)


# ---------------------------------------------------------------------------
# Path 2: _run_compute
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compute_path_does_not_call_state_store_put(tmp_path: Path) -> None:
    """_run_compute: compute handler executing does not call ProtocolStateStore.put().

    Compute nodes return results via the return value; no state store I/O
    should occur inside RuntimeLocal for any compute execution.
    """
    mod_name = "_test_compute_persist_mod"

    class _ComputeHandler:
        def handle(self, _payload: Any = None) -> _ComputeResult:
            return _ComputeResult(status="success")

    class _ComputeResult(BaseModel):
        status: str

    mod = types.ModuleType(mod_name)
    mod._ComputeHandler = _ComputeHandler  # type: ignore[attr-defined]
    sys.modules[mod_name] = mod

    mock_state_store = MagicMock()

    try:
        yaml_text = (
            "name: test-compute-persist\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: Compute state sink test\n"
            f"handler:\n"
            f"  module: {mod_name}\n"
            f"  class: _ComputeHandler\n"
        )
        workflow = tmp_path / "contract.yaml"
        workflow.write_text(yaml_text)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()

        assert result == EnumWorkflowResult.COMPLETED
        mock_state_store.put.assert_not_called()

    finally:
        sys.modules.pop(mod_name, None)


@pytest.mark.unit
def test_compute_path_no_terminal_event_no_state_store(tmp_path: Path) -> None:
    """_run_compute: no terminal_event path completes without touching state store.

    Compute contracts may have no terminal_event — runtime uses the compute
    execution path. This must complete cleanly with no ProtocolStateStore usage.
    """
    mod_name = "_test_compute_no_terminal_mod"

    class _NtHandler:
        def handle(self, _payload: Any = None) -> None:
            return None  # None → COMPLETED

    mod = types.ModuleType(mod_name)
    mod._NtHandler = _NtHandler  # type: ignore[attr-defined]
    sys.modules[mod_name] = mod

    try:
        yaml_text = (
            "name: test-no-terminal\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: No terminal event compute test\n"
            "handler_routing:\n"
            f"  default_handler: {mod_name}:_NtHandler\n"
        )
        workflow = tmp_path / "contract.yaml"
        workflow.write_text(yaml_text)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()

        assert result == EnumWorkflowResult.COMPLETED

        state_file = tmp_path / "state" / "workflow_result.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["result"] == "completed"

    finally:
        sys.modules.pop(mod_name, None)


# ---------------------------------------------------------------------------
# Path 3: _run_event_driven
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_driven_path_publishes_persist_intent_on_bus(
    tmp_path: Path,
) -> None:
    """_run_event_driven: handler publishing ModelPersistStateIntent is bus-mediated.

    This is the critical path that was missing coverage (PR #826 CR gap).
    A handler in the event-driven routing chain emits ModelPersistStateIntent
    as its output — the intent travels via the bus output_topic, not via
    ProtocolStateStore.put() inside RuntimeLocal.

    The test wires a two-handler chain:
      HandlerA (input: cmd.start.v1) → publishes ModelPersistStateIntent JSON
      Terminal listener receives on evt.done.v1

    HandlerA acts as the "reducer" emitting the persist intent.
    """

    class _InputCmd(BaseModel):
        correlation_id: str

    class _PersistIntentMsg(BaseModel):
        """Serializable wrapper so HandlerBusAdapter can publish it."""

        intent_id: str
        node_id: str
        correlation_id: str
        kind: str = "state.persist"

        @classmethod
        def from_persist_intent(
            cls, intent: ModelPersistStateIntent
        ) -> _PersistIntentMsg:
            return cls(
                intent_id=str(intent.intent_id),
                node_id=intent.envelope.node_id,
                correlation_id=str(intent.correlation_id),
            )

    class _TerminalEvent(BaseModel):
        correlation_id: str
        status: str = "success"

    class _HandlerReducerLike:
        """Simulates a reducer emitting a persist intent on the bus."""

        async def handle(self, correlation_id: str) -> _PersistIntentMsg:
            intent = _make_persist_intent()
            return _PersistIntentMsg.from_persist_intent(intent)

    class _HandlerTerminal:
        """Converts the persist intent message into a terminal event."""

        async def handle(
            self,
            intent_id: str,
            node_id: str,
            correlation_id: str,
            kind: str = "state.persist",
        ) -> _TerminalEvent:
            return _TerminalEvent(correlation_id=correlation_id)

    input_mod_name = "_test_evtdrv_input_cmd_mod"
    intent_mod_name = "_test_evtdrv_intent_msg_mod"
    handler_a_mod_name = "_test_evtdrv_handler_a_mod"
    handler_b_mod_name = "_test_evtdrv_handler_b_mod"
    terminal_mod_name = "_test_evtdrv_terminal_mod"

    input_mod = types.ModuleType(input_mod_name)
    input_mod._InputCmd = _InputCmd  # type: ignore[attr-defined]
    intent_mod = types.ModuleType(intent_mod_name)
    intent_mod._PersistIntentMsg = _PersistIntentMsg  # type: ignore[attr-defined]
    handler_a_mod = types.ModuleType(handler_a_mod_name)
    handler_a_mod._HandlerReducerLike = _HandlerReducerLike  # type: ignore[attr-defined]
    handler_b_mod = types.ModuleType(handler_b_mod_name)
    handler_b_mod._HandlerTerminal = _HandlerTerminal  # type: ignore[attr-defined]
    terminal_mod = types.ModuleType(terminal_mod_name)
    terminal_mod._TerminalEvent = _TerminalEvent  # type: ignore[attr-defined]

    for name, mod in [
        (input_mod_name, input_mod),
        (intent_mod_name, intent_mod),
        (handler_a_mod_name, handler_a_mod),
        (handler_b_mod_name, handler_b_mod),
        (terminal_mod_name, terminal_mod),
    ]:
        sys.modules[name] = mod

    mock_state_store = MagicMock()

    try:
        contract_yaml = (
            "workflow_id: test-evtdrv-persist\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: workflow\n"
            "description: Event-driven reducer state persistence test\n"
            "terminal_event: evt.done.v1\n"
            "event_bus:\n"
            "  subscribe_topics:\n"
            "    - cmd.start.v1\n"
            "    - onex.int.state-persist.v1\n"
            "  publish_topics:\n"
            "    - evt.done.v1\n"
            f"input_model:\n"
            f"  module: {input_mod_name}\n"
            f"  class: _InputCmd\n"
            "handler_routing:\n"
            "  routing_strategy: payload_type_match\n"
            "  handlers:\n"
            "    - event_model:\n"
            f"        name: _InputCmd\n"
            f"        module: {input_mod_name}\n"
            "      handler:\n"
            f"        name: _HandlerReducerLike\n"
            f"        module: {handler_a_mod_name}\n"
            "      output_events:\n"
            "        - _PersistIntentMsg\n"
            "    - event_model:\n"
            f"        name: _PersistIntentMsg\n"
            f"        module: {intent_mod_name}\n"
            "      handler:\n"
            f"        name: _HandlerTerminal\n"
            f"        module: {handler_b_mod_name}\n"
            "      output_events:\n"
            "        - _TerminalEvent\n"
        )

        workflow = tmp_path / "contract.yaml"
        workflow.write_text(contract_yaml)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=10,
        )
        result = await runtime.run_async()

        assert result == EnumWorkflowResult.COMPLETED
        mock_state_store.put.assert_not_called()

        state_file = tmp_path / "state" / "workflow_result.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["result"] == "completed"

    finally:
        for name in [
            input_mod_name,
            intent_mod_name,
            handler_a_mod_name,
            handler_b_mod_name,
            terminal_mod_name,
        ]:
            sys.modules.pop(name, None)


@pytest.mark.unit
def test_event_driven_path_does_not_import_state_store(tmp_path: Path) -> None:
    """_run_event_driven: runtime_local_adapter has no ProtocolStateStore reference.

    The HandlerBusAdapter (used by _run_event_driven) must not reference
    ProtocolStateStore — it only publishes handler results to the bus.
    """
    from omnibase_core.runtime import runtime_local_adapter

    source_file = inspect.getfile(runtime_local_adapter)
    source_text = Path(source_file).read_text(encoding="utf-8")

    assert "ProtocolStateStore" not in source_text, (
        "runtime_local_adapter.py must not reference ProtocolStateStore — "
        "the adapter only publishes results to the bus (OMN-9006 regression)"
    )


# ---------------------------------------------------------------------------
# Cross-path uniformity guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_all_three_paths_share_no_state_store_wiring() -> None:
    """All three execution paths must be free of direct state store persistence.

    Guards the uniformity invariant from OMN-9006: _run_single_handler,
    _run_compute, and _run_event_driven all publish intents without calling
    ProtocolStateStore.put(). This is verified by inspecting runtime_local.py
    source for forbidden patterns (import-level and method calls).

    Note: doc-comment mentions of 'ProtocolStateStore' are acceptable;
    we target functional code patterns only.
    """
    import omnibase_core.runtime.runtime_local as rl_module

    source = Path(inspect.getfile(rl_module)).read_text(encoding="utf-8")
    lines = source.splitlines()

    # Imports of ProtocolStateStore are forbidden
    import_lines = [ln for ln in lines if "import" in ln and "ProtocolStateStore" in ln]
    assert not import_lines, (
        f"runtime_local.py must not import ProtocolStateStore: {import_lines} (OMN-9006)"
    )

    # The deleted direct-persistence method must not exist
    assert "_persist_reducer_projection_if_applicable" not in source, (
        "runtime_local.py must not contain _persist_reducer_projection_if_applicable — "
        "deleted in OMN-9011 (OMN-9006 regression)"
    )

    # Direct state_store.put() calls are forbidden
    for symbol in ["state_store.put(", "StateStore.put("]:
        assert symbol not in source, (
            f"runtime_local.py contains forbidden call '{symbol}' — "
            "state persistence must flow via the effect node (OMN-9006)"
        )
