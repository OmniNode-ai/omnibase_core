# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ProtocolStateStore protocol and ModelStateEnvelope model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.protocols.storage.protocol_state_store import (
    ModelStateEnvelope,
    ProtocolStateStore,
    StateCorruptionError,
)


@pytest.mark.unit
class TestProtocolStateStore:
    """Tests for the ProtocolStateStore protocol definition."""

    def test_protocol_defines_required_methods(self) -> None:
        """Protocol defines get, put, delete, exists, list_keys."""
        required = {"get", "put", "delete", "exists", "list_keys"}
        members = {name for name in dir(ProtocolStateStore) if not name.startswith("_")}
        assert required.issubset(members), f"Missing: {required - members}"

    def test_runtime_checkable_with_compliant_impl(self) -> None:
        """A compliant dummy object passes isinstance check."""

        class _DummyStore:
            async def get(
                self, node_id: str, scope_id: str = "default"
            ) -> ModelStateEnvelope | None:
                return None

            async def put(self, envelope: ModelStateEnvelope) -> None:
                pass

            async def delete(self, node_id: str, scope_id: str = "default") -> bool:
                return False

            async def exists(self, node_id: str, scope_id: str = "default") -> bool:
                return False

            async def list_keys(
                self, node_id: str | None = None
            ) -> list[tuple[str, str]]:
                return []

        assert isinstance(_DummyStore(), ProtocolStateStore)

    def test_non_compliant_impl_fails_isinstance(self) -> None:
        """An object missing required methods fails isinstance check."""

        class _IncompleteStore:
            async def get(self, node_id: str) -> None:
                return None

        assert not isinstance(_IncompleteStore(), ProtocolStateStore)

    def test_protocol_is_runtime_checkable(self) -> None:
        """ProtocolStateStore can be used with isinstance at runtime."""
        assert hasattr(ProtocolStateStore, "__protocol_attrs__") or hasattr(
            ProtocolStateStore, "__abstractmethods__"
        )


@pytest.mark.unit
class TestModelStateEnvelope:
    """Tests for the ModelStateEnvelope Pydantic model."""

    def test_frozen_rejects_mutation(self) -> None:
        """ModelStateEnvelope is frozen and rejects field assignment."""
        envelope = ModelStateEnvelope(
            node_id="test",
            data={"x": 1},
            written_at=datetime.now(UTC),
        )
        with pytest.raises(Exception):
            envelope.node_id = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """ModelStateEnvelope rejects extra fields."""
        with pytest.raises(Exception):
            ModelStateEnvelope(
                node_id="test",
                data={},
                written_at=datetime.now(UTC),
                bad_field=True,  # type: ignore[call-arg]
            )

    def test_default_scope_id(self) -> None:
        """Default scope_id is 'default'."""
        envelope = ModelStateEnvelope(
            node_id="test",
            data={},
            written_at=datetime.now(UTC),
        )
        assert envelope.scope_id == "default"

    def test_default_contract_fingerprint(self) -> None:
        """Default contract_fingerprint is empty string."""
        envelope = ModelStateEnvelope(
            node_id="test",
            data={},
            written_at=datetime.now(UTC),
        )
        assert envelope.contract_fingerprint == ""

    def test_custom_values(self) -> None:
        """ModelStateEnvelope accepts custom scope_id and fingerprint."""
        now = datetime.now(UTC)
        envelope = ModelStateEnvelope(
            node_id="node-abc",
            scope_id="run-42",
            data={"count": 99},
            written_at=now,
            contract_fingerprint="sha256:abc123",
        )
        assert envelope.node_id == "node-abc"
        assert envelope.scope_id == "run-42"
        assert envelope.data == {"count": 99}
        assert envelope.written_at == now
        assert envelope.contract_fingerprint == "sha256:abc123"


@pytest.mark.unit
class TestStateCorruptionError:
    """Tests for the StateCorruptionError exception."""

    def test_is_exception(self) -> None:
        """StateCorruptionError is a proper Exception subclass."""
        assert issubclass(StateCorruptionError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """StateCorruptionError can be raised with a message."""
        with pytest.raises(StateCorruptionError, match="corrupt data"):
            raise StateCorruptionError("corrupt data at key foo/bar")
