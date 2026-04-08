# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for RuntimeLocal handler loading and execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.runtime.runtime_local import RuntimeLocal, load_workflow_contract
from omnibase_core.runtime.runtime_local_adapter import HandlerBusAdapter

# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------

VALID_WORKFLOW_YAML = (
    "workflow_id: test\n"
    "contract_version: {major: 1, minor: 0, patch: 0}\n"
    "node_type: workflow\n"
    "description: Test\n"
    "initial_command: cmd.test.v1\n"
    "terminal_event: evt.test.v1\n"
    "handler:\n"
    "  class: Foo\n"
    "  module: nonexistent.module\n"
    "nodes: []\n"
    "event_flow: []\n"
)


# -- Lightweight Pydantic models for adapter tests --

from pydantic import BaseModel


class MockInput(BaseModel):
    correlation_id: str
    name: str


class MockOutput(BaseModel):
    correlation_id: str
    result: str


# -- Mock bus & message --


class MockBus:
    """In-memory bus that records publish calls."""

    def __init__(self) -> None:
        self.published: list[tuple[str, bytes | None, bytes]] = []

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Any = None,
    ) -> None:
        self.published.append((topic, key, value))


class MockMessage:
    """Minimal message object carrying a byte payload."""

    def __init__(self, value: bytes) -> None:
        self.value = value


# ===================================================================
# Existing RuntimeLocal tests
# ===================================================================


@pytest.mark.unit
def test_load_workflow_contract_valid(tmp_path: Path) -> None:
    """load_workflow_contract returns parsed dict for valid YAML."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(VALID_WORKFLOW_YAML)
    data = load_workflow_contract(workflow)
    assert data["workflow_id"] == "test"
    assert data["handler"]["class"] == "Foo"


@pytest.mark.unit
def test_runtime_local_fails_on_bad_handler(tmp_path: Path) -> None:
    """RuntimeLocal returns FAILED when handler module cannot be imported."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(VALID_WORKFLOW_YAML)
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=tmp_path / "state",
        timeout=5,
    )
    result = runtime.run()
    assert result == EnumWorkflowResult.FAILED


@pytest.mark.unit
def test_runtime_local_writes_state(tmp_path: Path) -> None:
    """RuntimeLocal writes workflow_result.json to state_root."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(VALID_WORKFLOW_YAML)
    state_dir = tmp_path / "state"
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=state_dir,
        timeout=5,
    )
    runtime.run()
    result_file = state_dir / "workflow_result.json"
    assert result_file.exists()

    data = json.loads(result_file.read_text())
    assert data["result"] == "failed"
    assert data["exit_code"] == 1


@pytest.mark.unit
def test_runtime_local_missing_handler_spec(tmp_path: Path) -> None:
    """RuntimeLocal returns FAILED when handler section is missing."""
    workflow = tmp_path / "test.yaml"
    workflow.write_text(
        "workflow_id: test\n"
        "contract_version: {major: 1, minor: 0, patch: 0}\n"
        "node_type: workflow\n"
        "description: Test\n"
        "initial_command: cmd.test.v1\n"
        "terminal_event: evt.test.v1\n"
        "nodes: []\n"
        "event_flow: []\n"
    )
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=tmp_path / "state",
        timeout=5,
    )
    result = runtime.run()
    assert result == EnumWorkflowResult.FAILED


# ===================================================================
# HandlerBusAdapter unit tests
# ===================================================================


def _make_async_handler(
    output: MockOutput | None = None,
    error: Exception | None = None,
) -> Any:
    """Return an object with an async ``handle`` method."""

    class _Handler:
        calls: list[dict[str, Any]] = []

        async def handle(self, **kwargs: Any) -> MockOutput | None:
            self.calls.append(kwargs)
            if error is not None:
                raise error
            return output

    return _Handler()


def _make_sync_handler(
    output: MockOutput | None = None,
    error: Exception | None = None,
) -> Any:
    """Return an object with a sync ``handle`` method."""

    class _Handler:
        calls: list[dict[str, Any]] = []

        def handle(self, **kwargs: Any) -> MockOutput | None:
            self.calls.append(kwargs)
            if error is not None:
                raise error
            return output

    return _Handler()


def _input_bytes(correlation_id: str = "cid-1", name: str = "alice") -> bytes:
    return (
        MockInput(correlation_id=correlation_id, name=name).model_dump_json().encode()
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_async_handler() -> None:
    """Adapter deserializes message, calls async handler, publishes result."""
    expected_output = MockOutput(correlation_id="cid-1", result="ok")
    handler = _make_async_handler(output=expected_output)
    bus = MockBus()
    adapter = HandlerBusAdapter(
        handler=handler,
        handler_name="test-async",
        input_model_cls=MockInput,
        output_topic="out.topic",
        bus=bus,
    )

    msg = MockMessage(value=_input_bytes())
    await adapter.on_message(msg)

    # Handler was called with deserialized kwargs
    assert len(handler.calls) == 1
    assert handler.calls[0]["correlation_id"] == "cid-1"
    assert handler.calls[0]["name"] == "alice"

    # Result published to output topic
    assert len(bus.published) == 1
    topic, _key, value = bus.published[0]
    assert topic == "out.topic"
    published_data = json.loads(value)
    assert published_data["correlation_id"] == "cid-1"
    assert published_data["result"] == "ok"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_sync_handler() -> None:
    """Adapter works with sync handlers too."""
    expected_output = MockOutput(correlation_id="cid-2", result="sync-ok")
    handler = _make_sync_handler(output=expected_output)
    bus = MockBus()
    adapter = HandlerBusAdapter(
        handler=handler,
        handler_name="test-sync",
        input_model_cls=MockInput,
        output_topic="out.topic",
        bus=bus,
    )

    msg = MockMessage(value=_input_bytes(correlation_id="cid-2", name="bob"))
    await adapter.on_message(msg)

    assert len(handler.calls) == 1
    assert handler.calls[0]["name"] == "bob"
    assert len(bus.published) == 1
    published_data = json.loads(bus.published[0][2])
    assert published_data["result"] == "sync-ok"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_error_calls_on_error() -> None:
    """When handler raises, on_error callback is invoked."""
    handler = _make_async_handler(error=RuntimeError("boom"))
    bus = MockBus()
    error_called = False

    def _on_error() -> None:
        nonlocal error_called
        error_called = True

    adapter = HandlerBusAdapter(
        handler=handler,
        handler_name="test-err",
        input_model_cls=MockInput,
        output_topic="out.topic",
        bus=bus,
        on_error=_on_error,
    )

    msg = MockMessage(value=_input_bytes())
    await adapter.on_message(msg)

    assert error_called
    # Nothing published on error
    assert len(bus.published) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_bad_payload_calls_on_error() -> None:
    """When message value can't deserialize to input model, on_error fires."""
    handler = _make_async_handler()
    bus = MockBus()
    error_called = False

    def _on_error() -> None:
        nonlocal error_called
        error_called = True

    adapter = HandlerBusAdapter(
        handler=handler,
        handler_name="test-bad",
        input_model_cls=MockInput,
        output_topic="out.topic",
        bus=bus,
        on_error=_on_error,
    )

    # Payload missing required field "name"
    bad_payload = json.dumps({"correlation_id": "cid-x"}).encode()
    msg = MockMessage(value=bad_payload)
    await adapter.on_message(msg)

    assert error_called
    assert len(handler.calls) == 0
    assert len(bus.published) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_no_publish_when_no_output_topic() -> None:
    """When output_topic is None, adapter doesn't publish."""
    expected_output = MockOutput(correlation_id="cid-3", result="ignored")
    handler = _make_async_handler(output=expected_output)
    bus = MockBus()
    adapter = HandlerBusAdapter(
        handler=handler,
        handler_name="test-no-topic",
        input_model_cls=MockInput,
        output_topic=None,
        bus=bus,
    )

    msg = MockMessage(value=_input_bytes(correlation_id="cid-3"))
    await adapter.on_message(msg)

    assert len(handler.calls) == 1
    assert len(bus.published) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_preserves_correlation_id() -> None:
    """Correlation ID passes through input -> handler -> output."""
    cid = "unique-correlation-42"

    class _Handler:
        async def handle(self, **kwargs: Any) -> MockOutput:
            return MockOutput(correlation_id=kwargs["correlation_id"], result="traced")

    bus = MockBus()
    adapter = HandlerBusAdapter(
        handler=_Handler(),
        handler_name="test-cid",
        input_model_cls=MockInput,
        output_topic="trace.out",
        bus=bus,
    )

    msg = MockMessage(value=_input_bytes(correlation_id=cid, name="eve"))
    await adapter.on_message(msg)

    assert len(bus.published) == 1
    published_data = json.loads(bus.published[0][2])
    assert published_data["correlation_id"] == cid


# ===================================================================
# Routing detection tests (_has_event_routing)
# ===================================================================


def _runtime_with_contract(
    tmp_path: Path,
    extra_yaml: str = "",
) -> RuntimeLocal:
    """Create a RuntimeLocal and manually load a contract with extra fields."""
    yaml_text = VALID_WORKFLOW_YAML + extra_yaml
    workflow = tmp_path / "test.yaml"
    workflow.write_text(yaml_text)
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=tmp_path / "state",
        timeout=5,
    )
    # Load contract without running the full workflow
    import yaml

    runtime._contract = yaml.safe_load(yaml_text)
    return runtime


@pytest.mark.unit
def test_has_event_routing_valid(tmp_path: Path) -> None:
    """_has_event_routing returns True for valid handler_routing."""
    runtime = _runtime_with_contract(
        tmp_path,
        extra_yaml=(
            "handler_routing:\n"
            "  handlers:\n"
            "    - name: handler_a\n"
            "      module: mod_a\n"
            "      class: A\n"
        ),
    )
    assert runtime._has_event_routing() is True


@pytest.mark.unit
def test_has_event_routing_empty_handlers(tmp_path: Path) -> None:
    """_has_event_routing returns False when handlers list is empty."""
    runtime = _runtime_with_contract(
        tmp_path,
        extra_yaml="handler_routing:\n  handlers: []\n",
    )
    assert runtime._has_event_routing() is False


@pytest.mark.unit
def test_has_event_routing_missing(tmp_path: Path) -> None:
    """_has_event_routing returns False when no handler_routing."""
    runtime = _runtime_with_contract(tmp_path)
    assert runtime._has_event_routing() is False


@pytest.mark.unit
def test_has_event_routing_malformed(tmp_path: Path) -> None:
    """_has_event_routing returns False for non-dict handler_routing."""
    runtime = _runtime_with_contract(
        tmp_path,
        extra_yaml="handler_routing: not-a-dict\n",
    )
    assert runtime._has_event_routing() is False


# ===================================================================
# Compute mode tests (OMN-7605)
# ===================================================================


COMPUTE_CONTRACT_YAML = (
    "name: test_compute\n"
    "contract_version: {major: 1, minor: 0, patch: 0}\n"
    "node_type: compute\n"
    "description: Test compute node\n"
    "handler_routing:\n"
    "  default_handler: _test_compute_mod:TestComputeHandler\n"
)


@pytest.mark.unit
def test_compute_mode_no_terminal_event(tmp_path: Path) -> None:
    """Compute contracts without terminal_event use direct handler execution."""
    import sys
    import types

    class TestComputeHandler:
        def handle(self, _input: Any = None) -> Any:
            return type("R", (), {"status": "success"})()

    mod = types.ModuleType("_test_compute_mod")
    mod.TestComputeHandler = TestComputeHandler  # type: ignore[attr-defined]
    sys.modules["_test_compute_mod"] = mod

    try:
        workflow = tmp_path / "compute.yaml"
        workflow.write_text(COMPUTE_CONTRACT_YAML)
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()
        assert result == EnumWorkflowResult.COMPLETED
    finally:
        sys.modules.pop("_test_compute_mod", None)


@pytest.mark.unit
def test_compute_mode_handler_failure(tmp_path: Path) -> None:
    """Compute handler returning failure status yields FAILED result."""
    import sys
    import types

    class FailHandler:
        def handle(self, _input: Any = None) -> Any:
            return type("R", (), {"status": "failure"})()

    mod = types.ModuleType("_test_compute_fail_mod")
    mod.FailHandler = FailHandler  # type: ignore[attr-defined]
    sys.modules["_test_compute_fail_mod"] = mod

    try:
        yaml_text = (
            "name: test_fail\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: Failing compute\n"
            "handler_routing:\n"
            "  default_handler: _test_compute_fail_mod:FailHandler\n"
        )
        workflow = tmp_path / "fail.yaml"
        workflow.write_text(yaml_text)
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()
        assert result == EnumWorkflowResult.FAILED
    finally:
        sys.modules.pop("_test_compute_fail_mod", None)


@pytest.mark.unit
def test_compute_mode_writes_state(tmp_path: Path) -> None:
    """Compute mode writes workflow_result.json to state_root."""
    import sys
    import types

    class OkHandler:
        def handle(self, _input: Any = None) -> None:
            return None  # None -> COMPLETED

    mod = types.ModuleType("_test_compute_ok_mod")
    mod.OkHandler = OkHandler  # type: ignore[attr-defined]
    sys.modules["_test_compute_ok_mod"] = mod

    try:
        yaml_text = (
            "name: test_state\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: State write test\n"
            "handler_routing:\n"
            "  default_handler: _test_compute_ok_mod:OkHandler\n"
        )
        workflow = tmp_path / "state_test.yaml"
        workflow.write_text(yaml_text)
        state_dir = tmp_path / "state"
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=state_dir,
            timeout=5,
        )
        runtime.run()

        result_file = state_dir / "workflow_result.json"
        assert result_file.exists()
        data = json.loads(result_file.read_text())
        assert data["result"] == "completed"
        assert data["exit_code"] == 0
    finally:
        sys.modules.pop("_test_compute_ok_mod", None)


@pytest.mark.unit
def test_no_terminal_event_no_default_handler_fails(tmp_path: Path) -> None:
    """Contract with neither terminal_event nor default_handler fails."""
    yaml_text = (
        "name: broken\n"
        "contract_version: {major: 1, minor: 0, patch: 0}\n"
        "node_type: compute\n"
        "description: No handler\n"
    )
    workflow = tmp_path / "broken.yaml"
    workflow.write_text(yaml_text)
    runtime = RuntimeLocal(
        workflow_path=workflow,
        state_root=tmp_path / "state",
        timeout=5,
    )
    result = runtime.run()
    assert result == EnumWorkflowResult.FAILED


@pytest.mark.unit
def test_resolve_default_handler_bare_module(tmp_path: Path) -> None:
    """_resolve_default_handler resolves bare module name relative to contract."""
    # Create a fake package structure
    pkg_dir = tmp_path / "src" / "mypkg" / "nodes" / "node_foo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "src" / "mypkg" / "__init__.py").touch()
    (tmp_path / "src" / "mypkg" / "nodes" / "__init__.py").touch()
    (tmp_path / "src" / "mypkg" / "nodes" / "node_foo" / "__init__.py").touch()

    contract_path = pkg_dir / "contract.yaml"
    contract_path.write_text(
        "name: test\nhandler_routing:\n  default_handler: handler:MyHandler\n"
    )
    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=tmp_path / "state",
        timeout=5,
    )
    import yaml

    runtime._contract = yaml.safe_load(contract_path.read_text())

    result = runtime._resolve_default_handler()
    assert result is not None
    module_name, class_name = result
    assert class_name == "MyHandler"
    assert module_name == "mypkg.nodes.node_foo.handler"


# ===================================================================
# Integration test: two-handler chain
# ===================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_two_handler_chain_end_to_end(tmp_path: Path) -> None:
    """Two handlers chained via event bus, terminal event fires.

    Handler A: receives cmd.start (MockInput), emits MockMid
    Handler B: receives MockMid, emits MockTerminal
    Terminal listener receives on publish_topics -> COMPLETED
    """
    import sys
    import types

    class MockMid(BaseModel):
        correlation_id: str
        intermediate: str

    class MockTerminal(BaseModel):
        correlation_id: str
        done: bool

    # Handler A: MockInput -> MockMid
    class HandlerA:
        async def handle(self, correlation_id: str, name: str) -> MockMid:
            return MockMid(
                correlation_id=correlation_id, intermediate=f"processed-{name}"
            )

    # Handler B: MockMid -> MockTerminal
    class HandlerB:
        async def handle(self, correlation_id: str, intermediate: str) -> MockTerminal:
            return MockTerminal(correlation_id=correlation_id, done=True)

    # Register fake modules so importlib.import_module works
    mod_input = types.ModuleType("_test_chain_input")
    mod_input.MockInput = MockInput  # type: ignore[attr-defined]
    mod_mid = types.ModuleType("_test_chain_mid")
    mod_mid.MockMid = MockMid  # type: ignore[attr-defined]
    mod_handler_a = types.ModuleType("_test_chain_handler_a")
    mod_handler_a.HandlerA = HandlerA  # type: ignore[attr-defined]
    mod_handler_b = types.ModuleType("_test_chain_handler_b")
    mod_handler_b.HandlerB = HandlerB  # type: ignore[attr-defined]

    sys.modules["_test_chain_input"] = mod_input
    sys.modules["_test_chain_mid"] = mod_mid
    sys.modules["_test_chain_handler_a"] = mod_handler_a
    sys.modules["_test_chain_handler_b"] = mod_handler_b

    try:
        # --- Write contract YAML ---
        contract_yaml = (
            "workflow_id: test_chain\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: workflow\n"
            "description: Two-handler chain test\n"
            "initial_command: cmd.start.v1\n"
            "terminal_event: evt.done.v1\n"
            "event_bus:\n"
            "  subscribe_topics:\n"
            "    - cmd.start.v1\n"
            "    - evt.mid.v1\n"
            "  publish_topics:\n"
            "    - evt.done.v1\n"
            "input_model:\n"
            "  module: _test_chain_input\n"
            "  class: MockInput\n"
            "handler_routing:\n"
            "  routing_strategy: payload_type_match\n"
            "  handlers:\n"
            "    - event_model:\n"
            "        name: MockInput\n"
            "        module: _test_chain_input\n"
            "      handler:\n"
            "        name: HandlerA\n"
            "        module: _test_chain_handler_a\n"
            "      output_events:\n"
            "        - MockMid\n"
            "    - event_model:\n"
            "        name: MockMid\n"
            "        module: _test_chain_mid\n"
            "      handler:\n"
            "        name: HandlerB\n"
            "        module: _test_chain_handler_b\n"
            "      output_events:\n"
            "        - MockTerminal\n"
        )

        workflow = tmp_path / "chain_test.yaml"
        workflow.write_text(contract_yaml)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=10,
        )
        result = await runtime.run_async()

        assert result == EnumWorkflowResult.COMPLETED

        # Verify state was written
        state_file = tmp_path / "state" / "workflow_result.json"
        assert state_file.exists()
        state_data = json.loads(state_file.read_text())
        assert state_data["result"] == "completed"
        assert state_data["exit_code"] == 0

    finally:
        # Clean up fake modules
        for mod_name in [
            "_test_chain_input",
            "_test_chain_mid",
            "_test_chain_handler_a",
            "_test_chain_handler_b",
        ]:
            sys.modules.pop(mod_name, None)


# ===================================================================
# Fallback method resolution tests (OMN-7788, OMN-7789)
# ===================================================================


@pytest.mark.unit
def test_single_handler_fallback_to_run_full_cycle(tmp_path: Path) -> None:
    """Handler without handle() but with run_full_cycle() completes."""
    import sys
    import types

    class FakeResult(BaseModel):
        cycles_failed: int = 0
        status: str = "success"

    class FakeHandler:
        def run_full_cycle(self, command: Any = None) -> tuple[Any, list, FakeResult]:
            return (None, [], FakeResult())

    mod = types.ModuleType("_test_fallback_rfc_mod")
    mod.FakeHandler = FakeHandler  # type: ignore[attr-defined]
    sys.modules["_test_fallback_rfc_mod"] = mod

    try:
        yaml_text = (
            "name: test_rfc\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: Fallback test\n"
            "terminal_event: evt.done.v1\n"
            "handler:\n"
            "  module: _test_fallback_rfc_mod\n"
            "  class: FakeHandler\n"
        )
        workflow = tmp_path / "test.yaml"
        workflow.write_text(yaml_text)
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()
        assert result == EnumWorkflowResult.COMPLETED
    finally:
        sys.modules.pop("_test_fallback_rfc_mod", None)


@pytest.mark.unit
def test_single_handler_fallback_to_run(tmp_path: Path) -> None:
    """Handler without handle() but with run() completes."""
    import sys
    import types

    class RunResult(BaseModel):
        status: str = "ok"

    class RunHandler:
        def run(self, payload: Any = None) -> RunResult:
            return RunResult()

    mod = types.ModuleType("_test_fallback_run_mod")
    mod.RunHandler = RunHandler  # type: ignore[attr-defined]
    sys.modules["_test_fallback_run_mod"] = mod

    try:
        yaml_text = (
            "name: test_run\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: Fallback run test\n"
            "terminal_event: evt.done.v1\n"
            "handler:\n"
            "  module: _test_fallback_run_mod\n"
            "  class: RunHandler\n"
        )
        workflow = tmp_path / "test.yaml"
        workflow.write_text(yaml_text)
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()
        assert result == EnumWorkflowResult.COMPLETED
    finally:
        sys.modules.pop("_test_fallback_run_mod", None)


@pytest.mark.unit
def test_compute_mode_with_top_level_handler_spec(tmp_path: Path) -> None:
    """Compute node without terminal_event uses top-level handler spec (OMN-7789)."""
    import sys
    import types

    class ComputeResult(BaseModel):
        status: str = "ok"

    class TopLevelHandler:
        def handle(self, payload: Any = None) -> ComputeResult:
            return ComputeResult()

    mod = types.ModuleType("_test_toplevel_handler_mod")
    mod.TopLevelHandler = TopLevelHandler  # type: ignore[attr-defined]
    sys.modules["_test_toplevel_handler_mod"] = mod

    try:
        yaml_text = (
            "name: test_toplevel\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: Top-level handler compute test\n"
            "handler:\n"
            "  module: _test_toplevel_handler_mod\n"
            "  class: TopLevelHandler\n"
        )
        workflow = tmp_path / "test.yaml"
        workflow.write_text(yaml_text)
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()
        assert result == EnumWorkflowResult.COMPLETED
    finally:
        sys.modules.pop("_test_toplevel_handler_mod", None)


@pytest.mark.unit
def test_compute_mode_fallback_run_full_cycle(tmp_path: Path) -> None:
    """Compute node without terminal_event + no handle() falls back to run_full_cycle (OMN-7788)."""
    import sys
    import types

    class CycleResult(BaseModel):
        cycles_failed: int = 0

    class CycleHandler:
        def run_full_cycle(self, command: Any = None) -> tuple[Any, list, CycleResult]:
            return (None, [], CycleResult())

    mod = types.ModuleType("_test_compute_rfc_mod")
    mod.CycleHandler = CycleHandler  # type: ignore[attr-defined]
    sys.modules["_test_compute_rfc_mod"] = mod

    try:
        yaml_text = (
            "name: test_compute_rfc\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: Compute fallback test\n"
            "handler:\n"
            "  module: _test_compute_rfc_mod\n"
            "  class: CycleHandler\n"
        )
        workflow = tmp_path / "test.yaml"
        workflow.write_text(yaml_text)
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = runtime.run()
        assert result == EnumWorkflowResult.COMPLETED
    finally:
        sys.modules.pop("_test_compute_rfc_mod", None)
