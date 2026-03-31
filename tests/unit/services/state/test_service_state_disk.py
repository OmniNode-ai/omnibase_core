# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ServiceStateDisk file-based state store."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from omnibase_core.errors.error_state_corruption import StateCorruptionError
from omnibase_core.models.state.model_state_envelope import ModelStateEnvelope
from omnibase_core.protocols.storage.protocol_state_store import ProtocolStateStore
from omnibase_core.services.state.service_state_disk import ServiceStateDisk


@pytest.mark.unit
def test_implements_protocol() -> None:
    """ServiceStateDisk satisfies ProtocolStateStore isinstance check."""
    store = ServiceStateDisk(state_root=Path("/tmp/unused"))
    assert isinstance(store, ProtocolStateStore)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_put_and_get(tmp_path: Path) -> None:
    """Put an envelope and get it back with all fields intact."""
    store = ServiceStateDisk(state_root=tmp_path)
    envelope = ModelStateEnvelope(
        node_id="node_test",
        scope_id="run-1",
        data={"count": 42},
        written_at=datetime.now(UTC),
        contract_fingerprint="abc123",
    )
    await store.put(envelope)
    result = await store.get("node_test", "run-1")
    assert result is not None
    assert result.data == {"count": 42}
    assert result.contract_fingerprint == "abc123"
    assert result.node_id == "node_test"
    assert result.scope_id == "run-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_missing_returns_none(tmp_path: Path) -> None:
    """Getting nonexistent state returns None."""
    store = ServiceStateDisk(state_root=tmp_path)
    result = await store.get("nonexistent")
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_corruption_raises_error(tmp_path: Path) -> None:
    """Corrupt YAML file raises StateCorruptionError, not None."""
    store = ServiceStateDisk(state_root=tmp_path)
    state_dir = tmp_path / "corrupt_node" / "default"
    state_dir.mkdir(parents=True)
    (state_dir / "state.yaml").write_text("{{{{not valid yaml: [")
    with pytest.raises(StateCorruptionError):
        await store.get("corrupt_node")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_state_file_layout(tmp_path: Path) -> None:
    """State is written to {state_root}/{node_id}/{scope_id}/state.yaml."""
    store = ServiceStateDisk(state_root=tmp_path)
    envelope = ModelStateEnvelope(
        node_id="node_foo",
        scope_id="run-42",
        data={"x": 1},
        written_at=datetime.now(UTC),
    )
    await store.put(envelope)
    expected_path = tmp_path / "node_foo" / "run-42" / "state.yaml"
    assert expected_path.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_existing(tmp_path: Path) -> None:
    """Delete returns True for existing state and removes it."""
    store = ServiceStateDisk(state_root=tmp_path)
    envelope = ModelStateEnvelope(
        node_id="node_del",
        data={"x": 1},
        written_at=datetime.now(UTC),
    )
    await store.put(envelope)
    assert await store.delete("node_del") is True
    assert await store.get("node_del") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_missing_returns_false(tmp_path: Path) -> None:
    """Delete returns False for nonexistent state."""
    store = ServiceStateDisk(state_root=tmp_path)
    assert await store.delete("nonexistent") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_keys_filtered(tmp_path: Path) -> None:
    """list_keys with node_id returns sorted (node_id, scope_id) tuples."""
    store = ServiceStateDisk(state_root=tmp_path)
    for i in range(3):
        await store.put(
            ModelStateEnvelope(
                node_id="node_list",
                scope_id=f"run-{i}",
                data={},
                written_at=datetime.now(UTC),
            )
        )
    keys = await store.list_keys("node_list")
    assert keys == [
        ("node_list", "run-0"),
        ("node_list", "run-1"),
        ("node_list", "run-2"),
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_keys_all(tmp_path: Path) -> None:
    """list_keys without node_id returns all keys sorted."""
    store = ServiceStateDisk(state_root=tmp_path)
    await store.put(
        ModelStateEnvelope(node_id="bbb", data={}, written_at=datetime.now(UTC))
    )
    await store.put(
        ModelStateEnvelope(node_id="aaa", data={}, written_at=datetime.now(UTC))
    )
    keys = await store.list_keys()
    assert keys == [("aaa", "default"), ("bbb", "default")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exists(tmp_path: Path) -> None:
    """exists() returns True after put, False after delete."""
    store = ServiceStateDisk(state_root=tmp_path)
    assert await store.exists("node_ex") is False
    await store.put(
        ModelStateEnvelope(node_id="node_ex", data={}, written_at=datetime.now(UTC))
    )
    assert await store.exists("node_ex") is True
    await store.delete("node_ex")
    assert await store.exists("node_ex") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_put_overwrites(tmp_path: Path) -> None:
    """Second put overwrites the first."""
    store = ServiceStateDisk(state_root=tmp_path)
    await store.put(
        ModelStateEnvelope(
            node_id="node_ow",
            data={"v": 1},
            written_at=datetime.now(UTC),
        )
    )
    await store.put(
        ModelStateEnvelope(
            node_id="node_ow",
            data={"v": 2},
            written_at=datetime.now(UTC),
        )
    )
    result = await store.get("node_ow")
    assert result is not None
    assert result.data == {"v": 2}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schema_mismatch_raises_corruption(tmp_path: Path) -> None:
    """Valid YAML but invalid schema raises StateCorruptionError."""
    store = ServiceStateDisk(state_root=tmp_path)
    state_dir = tmp_path / "bad_schema" / "default"
    state_dir.mkdir(parents=True)
    (state_dir / "state.yaml").write_text("just_a_string: true\n")
    with pytest.raises(StateCorruptionError):
        await store.get("bad_schema")
