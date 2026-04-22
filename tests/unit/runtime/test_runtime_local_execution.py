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
def test_compute_mode_persists_handler_result(tmp_path: Path) -> None:
    """Compute mode sets _handler_result and writes handler_result to workflow_result.json.

    Regression: _run_compute() previously classified result_obj but never assigned
    self._handler_result, so workflow_result.json omitted 'handler_result' for the
    main CLI path (onex node <name> --input <file>). OMN-9467.
    """
    import sys
    import types

    from pydantic import BaseModel

    class _HandlerOutput(BaseModel):
        status: str
        data: str

    class _ResultHandler:
        def handle(self, _input: Any = None) -> _HandlerOutput:
            return _HandlerOutput(status="success", data="compute-result")

    mod = types.ModuleType("_test_compute_handler_result_mod")
    mod._ResultHandler = _ResultHandler  # type: ignore[attr-defined]
    sys.modules["_test_compute_handler_result_mod"] = mod

    try:
        yaml_text = (
            "name: test_handler_result\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: compute\n"
            "description: handler_result persistence test\n"
            "handler_routing:\n"
            "  default_handler: _test_compute_handler_result_mod:_ResultHandler\n"
        )
        workflow = tmp_path / "handler_result.yaml"
        workflow.write_text(yaml_text)
        state_dir = tmp_path / "state"
        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=state_dir,
            timeout=5,
        )
        result = runtime.run()
        assert result == EnumWorkflowResult.COMPLETED

        # _handler_result must be set on the runtime instance
        assert runtime._handler_result is not None
        assert isinstance(runtime._handler_result, _HandlerOutput)
        assert runtime._handler_result.data == "compute-result"

        # workflow_result.json must include handler_result
        result_file = state_dir / "workflow_result.json"
        assert result_file.exists()
        data = json.loads(result_file.read_text())
        assert "handler_result" in data, (
            "handler_result missing from workflow_result.json"
        )
        assert data["handler_result"]["status"] == "success"
        assert data["handler_result"]["data"] == "compute-result"
    finally:
        sys.modules.pop("_test_compute_handler_result_mod", None)


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


# ===================================================================
# handler_routing.default_handler resolution tests
# ===================================================================


@pytest.mark.unit
def test_resolve_default_handler_returns_none_when_no_routing(
    tmp_path: Path,
) -> None:
    """_resolve_default_handler returns None when handler_routing is absent."""
    runtime = _runtime_with_contract(tmp_path)
    assert runtime._resolve_default_handler() is None


@pytest.mark.unit
def test_resolve_default_handler_returns_none_for_malformed(
    tmp_path: Path,
) -> None:
    """_resolve_default_handler returns None for non-dict handler_routing."""
    runtime = _runtime_with_contract(
        tmp_path,
        extra_yaml="handler_routing: not-a-dict\n",
    )
    assert runtime._resolve_default_handler() is None


@pytest.mark.unit
def test_resolve_default_handler_returns_none_without_colon(
    tmp_path: Path,
) -> None:
    """_resolve_default_handler returns None when default_handler has no colon."""
    runtime = _runtime_with_contract(
        tmp_path,
        extra_yaml="handler_routing:\n  default_handler: NoColonHere\n",
    )
    assert runtime._resolve_default_handler() is None


@pytest.mark.unit
def test_resolve_default_handler_parses_handler_colon_format(
    tmp_path: Path,
) -> None:
    """_resolve_default_handler resolves handler:ClassName from a Python package dir."""
    import sys as _sys

    # Create a fake Python package in tmp_path so the contract dir is importable
    pkg_dir = tmp_path / "fake_pkg" / "nodes" / "node_test"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "fake_pkg" / "__init__.py").touch()
    (tmp_path / "fake_pkg" / "nodes" / "__init__.py").touch()
    (pkg_dir / "__init__.py").touch()

    contract = pkg_dir / "contract.yaml"
    contract.write_text(
        "workflow_id: test\n"
        "contract_version: {major: 1, minor: 0, patch: 0}\n"
        "node_type: workflow\n"
        "description: Test\n"
        "terminal_event: evt.test.v1\n"
        "handler_routing:\n"
        "  default_handler: handler:MyHandler\n"
    )

    # Add tmp_path to sys.path so the module can be resolved
    _sys.path.insert(0, str(tmp_path))
    try:
        runtime = RuntimeLocal(
            workflow_path=contract,
            state_root=tmp_path / "state",
            timeout=5,
        )
        import yaml

        runtime._contract = yaml.safe_load(contract.read_text())

        result = runtime._resolve_default_handler()
        assert result is not None
        module_name, class_name = result
        assert module_name == "fake_pkg.nodes.node_test.handler"
        assert class_name == "MyHandler"
    finally:
        _sys.path.remove(str(tmp_path))


@pytest.mark.unit
def test_resolve_default_handler_no_init_py(tmp_path: Path) -> None:
    """_resolve_default_handler returns None when contract dir has no __init__.py."""
    pkg_dir = tmp_path / "not_a_package"
    pkg_dir.mkdir(parents=True)

    contract = pkg_dir / "contract.yaml"
    contract.write_text(
        "workflow_id: test\n"
        "contract_version: {major: 1, minor: 0, patch: 0}\n"
        "node_type: workflow\n"
        "description: Test\n"
        "terminal_event: evt.test.v1\n"
        "handler_routing:\n"
        "  default_handler: handler:MyHandler\n"
    )

    runtime = RuntimeLocal(
        workflow_path=contract,
        state_root=tmp_path / "state",
        timeout=5,
    )
    import yaml

    runtime._contract = yaml.safe_load(contract.read_text())

    assert runtime._resolve_default_handler() is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_single_handler_falls_back_to_default_handler(
    tmp_path: Path,
) -> None:
    """_run_single_handler uses handler_routing.default_handler when handler spec is missing."""
    import sys as _sys
    import types

    # Create a fake handler class
    class FakeHandler:
        def handle(self, _payload: Any) -> Any:
            return type("R", (), {"status": "success"})()

    fake_mod = types.ModuleType("_test_default_handler_pkg")
    fake_mod.FakeHandler = FakeHandler  # type: ignore[attr-defined]
    _sys.modules["_test_default_handler_pkg"] = fake_mod

    fake_handler_mod = types.ModuleType("_test_default_handler_pkg.handler")
    fake_handler_mod.FakeHandler = FakeHandler  # type: ignore[attr-defined]
    _sys.modules["_test_default_handler_pkg.handler"] = fake_handler_mod

    # Create a package directory with __init__.py
    pkg_dir = tmp_path / "_test_default_handler_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    contract = pkg_dir / "contract.yaml"
    contract.write_text(
        "workflow_id: test_default\n"
        "contract_version: {major: 1, minor: 0, patch: 0}\n"
        "node_type: workflow\n"
        "description: Test default handler fallback\n"
        "terminal_event: evt.done.v1\n"
        "handler_routing:\n"
        "  default_handler: handler:FakeHandler\n"
    )

    _sys.path.insert(0, str(tmp_path))
    try:
        runtime = RuntimeLocal(
            workflow_path=contract,
            state_root=tmp_path / "state",
            timeout=5,
        )
        result = await runtime.run_async()
        assert result == EnumWorkflowResult.COMPLETED
    finally:
        _sys.path.remove(str(tmp_path))
        _sys.modules.pop("_test_default_handler_pkg.handler", None)
        _sys.modules.pop("_test_default_handler_pkg", None)


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
@pytest.mark.asyncio
async def test_adapter_dict_return_publishes_json() -> None:
    """Reducer returning dict → bus receives valid JSON envelope."""

    class DictHandler:
        async def handle(self, **kwargs: Any) -> dict[str, Any]:
            return {"correlation_id": kwargs.get("correlation_id"), "status": "ok"}

    bus = MockBus()
    adapter = HandlerBusAdapter(
        handler=DictHandler(),
        handler_name="test-dict",
        input_model_cls=MockInput,
        output_topic="out.dict",
        bus=bus,
    )

    msg = MockMessage(value=_input_bytes(correlation_id="cid-dict"))
    await adapter.on_message(msg)

    assert len(bus.published) == 1
    topic, _key, value = bus.published[0]
    assert topic == "out.dict"
    data = json.loads(value)
    assert data["correlation_id"] == "cid-dict"
    assert data["status"] == "ok"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_none_return_no_publish() -> None:
    """Handler returning None → no message published."""

    class NoneHandler:
        async def handle(self, **kwargs: Any) -> None:
            return None

    bus = MockBus()
    adapter = HandlerBusAdapter(
        handler=NoneHandler(),
        handler_name="test-none",
        input_model_cls=MockInput,
        output_topic="out.none",
        bus=bus,
    )

    msg = MockMessage(value=_input_bytes(correlation_id="cid-none"))
    await adapter.on_message(msg)

    assert len(bus.published) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_unsupported_return_type_raises_on_error() -> None:
    """Handler returning unsupported type → ModelOnexError raised, on_error fires, nothing published."""

    class IntHandler:
        async def handle(self, **kwargs: Any) -> int:
            return 42

    bus = MockBus()
    error_called = False

    def _on_error() -> None:
        nonlocal error_called
        error_called = True

    adapter = HandlerBusAdapter(
        handler=IntHandler(),
        handler_name="test-int",
        input_model_cls=MockInput,
        output_topic="out.int",
        bus=bus,
        on_error=_on_error,
    )

    msg = MockMessage(value=_input_bytes(correlation_id="cid-int"))
    await adapter.on_message(msg)

    assert error_called
    assert len(bus.published) == 0


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


# ===================================================================
# _validate_routing map-based checks (OMN-9262)
# ===================================================================


def _make_handler_entry(
    event_name: str = "MyEvent",
    event_module: str = "mod.events",
    handler_name: str = "MyHandler",
    handler_module: str = "mod.handlers",
    output_events: list[str] | None = None,
    subscribe_topic: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "event_model": {"name": event_name, "module": event_module},
        "handler": {"name": handler_name, "module": handler_module},
        "output_events": output_events or [],
    }
    if subscribe_topic is not None:
        entry["subscribe_topic"] = subscribe_topic
    return entry


@pytest.mark.unit
def test_validate_routing_map_based_happy_path() -> None:
    """Map-based validation passes when all handlers have input topics in subscribe_topics."""
    routing = {
        "handlers": [
            _make_handler_entry(
                "EventA", handler_name="HandlerA", output_events=["EventB"]
            ),
            _make_handler_entry("EventB", handler_name="HandlerB"),
        ]
    }
    errors = RuntimeLocal._validate_routing(
        routing,
        subscribe_topics=["topic.a.v1", "topic.b.v1"],
        publish_topics=["topic.done.v1"],
    )
    assert errors == []


@pytest.mark.unit
def test_validate_routing_terminal_reducer_no_padding() -> None:
    """Terminal reducer with explicit subscribe_topic requires no padding of subscribe_topics."""
    routing = {
        "handlers": [
            _make_handler_entry(
                "EventA",
                handler_name="HandlerA",
                output_events=["EventB"],
            ),
            _make_handler_entry(
                "EventB",
                handler_name="HandlerB",
                subscribe_topic="topic.b.v1",
            ),
        ]
    }
    # Only one subscribe_topic declared (for HandlerA); HandlerB uses explicit field.
    errors = RuntimeLocal._validate_routing(
        routing,
        subscribe_topics=["topic.a.v1", "topic.b.v1"],
        publish_topics=[],
    )
    assert errors == []


@pytest.mark.unit
def test_validate_routing_terminal_reducer_no_input_topic() -> None:
    """Terminal reducer with no subscribe_topic and no positional slot is valid (no bus wiring)."""
    routing = {
        "handlers": [
            _make_handler_entry("EventA", handler_name="HandlerA"),
            # Handler at index 1, but subscribe_topics only has 1 entry — no slot.
            _make_handler_entry("EventB", handler_name="TerminalReducer"),
        ]
    }
    errors = RuntimeLocal._validate_routing(
        routing,
        subscribe_topics=["topic.a.v1"],
        publish_topics=[],
    )
    assert errors == []


@pytest.mark.unit
def test_validate_routing_explicit_subscribe_topic_not_in_list() -> None:
    """Explicit subscribe_topic that is not in subscribe_topics is an error."""
    routing = {
        "handlers": [
            _make_handler_entry(
                "EventA",
                handler_name="HandlerA",
                subscribe_topic="topic.unknown.v1",
            ),
        ]
    }
    errors = RuntimeLocal._validate_routing(
        routing,
        subscribe_topics=["topic.a.v1"],
        publish_topics=[],
    )
    assert len(errors) == 1
    assert "topic.unknown.v1" in errors[0]
    assert "not in event_bus.subscribe_topics" in errors[0]


@pytest.mark.unit
def test_validate_routing_orphan_output_still_detected() -> None:
    """Orphan output_events (no downstream and no publish_topics) still produces an error."""
    routing = {
        "handlers": [
            _make_handler_entry(
                "EventA",
                handler_name="HandlerA",
                output_events=["UnknownEvent"],
            ),
        ]
    }
    errors = RuntimeLocal._validate_routing(
        routing,
        subscribe_topics=["topic.a.v1"],
        publish_topics=[],
    )
    assert any("UnknownEvent" in e for e in errors)


@pytest.mark.unit
def test_validate_routing_missing_required_fields() -> None:
    """Missing event_model.name / handler.module are still caught."""
    routing = {
        "handlers": [
            {
                "event_model": {"module": "mod.events"},
                "handler": {"name": "HandlerA"},
                "output_events": [],
            }
        ]
    }
    errors = RuntimeLocal._validate_routing(
        routing,
        subscribe_topics=["topic.a.v1"],
        publish_topics=[],
    )
    assert any("event_model.name is missing" in e for e in errors)
    assert any("handler.module is missing" in e for e in errors)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_terminal_reducer_end_to_end(tmp_path: Path) -> None:
    """Terminal reducer workflow: three-handler chain where HandlerC is terminal.

    HandlerA: cmd.start.v1 → EventB (on evt.mid.v1)
    HandlerB: evt.mid.v1 → EventC (on evt.done.v1, terminal)
    HandlerC: subscribe_topic: evt.done.v1, no output_events — terminal reducer.

    HandlerC uses an explicit subscribe_topic with no padding required.
    The terminal event fires when HandlerB publishes EventC to evt.done.v1.
    HandlerC is wired to evt.done.v1 via explicit subscribe_topic, and the
    side-effect assertion verifies it actually ran.
    """
    import sys
    import types

    class EventA(BaseModel):
        correlation_id: str

    class EventB(BaseModel):
        correlation_id: str
        step: str = "mid"

    class EventC(BaseModel):
        correlation_id: str
        step: str = "done"
        status: str = "success"

    class HandlerA:
        async def handle(self, correlation_id: str) -> EventB:
            return EventB(correlation_id=correlation_id)

    class HandlerB:
        async def handle(self, correlation_id: str, step: str) -> EventC:
            return EventC(correlation_id=correlation_id)

    terminal_calls: list[str] = []

    class HandlerCTerminal:
        """Terminal reducer — processes EventC but has no output_events.

        Uses explicit subscribe_topic without requiring positional padding.
        """

        async def handle(self, correlation_id: str, step: str, status: str) -> None:
            terminal_calls.append(correlation_id)

    mod_event_a = types.ModuleType("_test_tr2_event_a")
    mod_event_a.EventA = EventA  # type: ignore[attr-defined]
    mod_event_b = types.ModuleType("_test_tr2_event_b")
    mod_event_b.EventB = EventB  # type: ignore[attr-defined]
    mod_event_c = types.ModuleType("_test_tr2_event_c")
    mod_event_c.EventC = EventC  # type: ignore[attr-defined]
    mod_handler_a = types.ModuleType("_test_tr2_handler_a")
    mod_handler_a.HandlerA = HandlerA  # type: ignore[attr-defined]
    mod_handler_b = types.ModuleType("_test_tr2_handler_b")
    mod_handler_b.HandlerB = HandlerB  # type: ignore[attr-defined]
    mod_handler_c = types.ModuleType("_test_tr2_handler_c")
    mod_handler_c.HandlerCTerminal = HandlerCTerminal  # type: ignore[attr-defined]

    for name, mod in [
        ("_test_tr2_event_a", mod_event_a),
        ("_test_tr2_event_b", mod_event_b),
        ("_test_tr2_event_c", mod_event_c),
        ("_test_tr2_handler_a", mod_handler_a),
        ("_test_tr2_handler_b", mod_handler_b),
        ("_test_tr2_handler_c", mod_handler_c),
    ]:
        sys.modules[name] = mod

    try:
        # subscribe_topics contains evt.done.v1 so HandlerC can wire to it.
        # publish_topics also contains evt.done.v1 as the terminal.
        # HandlerC uses explicit subscribe_topic — no positional padding required
        # (only 2 handlers use positional slots; HandlerC uses its own field).
        contract_yaml = (
            "workflow_id: test_terminal_reducer\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: workflow\n"
            "description: Terminal reducer test\n"
            "initial_command: cmd.start.v1\n"
            "terminal_event: evt.done.v1\n"
            "event_bus:\n"
            "  subscribe_topics:\n"
            "    - cmd.start.v1\n"
            "    - evt.mid.v1\n"
            "    - evt.done.v1\n"
            "  publish_topics:\n"
            "    - evt.done.v1\n"
            "input_model:\n"
            "  module: _test_tr2_event_a\n"
            "  class: EventA\n"
            "handler_routing:\n"
            "  routing_strategy: payload_type_match\n"
            "  handlers:\n"
            "    - event_model:\n"
            "        name: EventA\n"
            "        module: _test_tr2_event_a\n"
            "      handler:\n"
            "        name: HandlerA\n"
            "        module: _test_tr2_handler_a\n"
            "      output_events:\n"
            "        - EventB\n"
            "    - event_model:\n"
            "        name: EventB\n"
            "        module: _test_tr2_event_b\n"
            "      handler:\n"
            "        name: HandlerB\n"
            "        module: _test_tr2_handler_b\n"
            "      output_events:\n"
            "        - EventC\n"
            "    - event_model:\n"
            "        name: EventC\n"
            "        module: _test_tr2_event_c\n"
            "      handler:\n"
            "        name: HandlerCTerminal\n"
            "        module: _test_tr2_handler_c\n"
            "      subscribe_topic: evt.done.v1\n"
            "      output_events: []\n"
        )
        workflow = tmp_path / "terminal_reducer.yaml"
        workflow.write_text(contract_yaml)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=10,
        )
        result = await runtime.run_async()
        assert result == EnumWorkflowResult.COMPLETED
        assert len(terminal_calls) > 0, "HandlerCTerminal was never invoked"

    finally:
        for name in [
            "_test_tr2_event_a",
            "_test_tr2_event_b",
            "_test_tr2_event_c",
            "_test_tr2_handler_a",
            "_test_tr2_handler_b",
            "_test_tr2_handler_c",
        ]:
            sys.modules.pop(name, None)
