# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDispatchClaim and compute_blocker_id (OMN-8922)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.dispatch.model_dispatch_claim import (
    ModelDispatchClaim,
    compute_blocker_id,
)


def _make_claim(**overrides) -> ModelDispatchClaim:
    defaults: dict = {
        "blocker_id": compute_blocker_id("fix_containers", "192.168.86.201", "docker"),
        "kind": "fix_containers",
        "host": "192.168.86.201",
        "resource": "docker",
        "claimant": "agent-abc123",
        "claimed_at": datetime.now(tz=UTC),
        "ttl_seconds": 300,
        "tool_name": "Agent",
    }
    defaults.update(overrides)
    return ModelDispatchClaim(**defaults)


@pytest.mark.unit
def test_blocker_id_determinism() -> None:
    id1 = compute_blocker_id("fix_containers", "192.168.86.201", "res")
    id2 = compute_blocker_id("fix_containers", "192.168.86.201", "res")
    assert id1 == id2
    assert len(id1) == 40


@pytest.mark.unit
def test_blocker_id_distinct_inputs() -> None:
    id1 = compute_blocker_id("fix_containers", "192.168.86.201", "docker")
    id2 = compute_blocker_id("fix_containers", "192.168.86.201", "redpanda")
    assert id1 != id2


@pytest.mark.unit
def test_blocker_id_resource_order_stable() -> None:
    # kind|host|resource ordering must be stable — swapping parts changes the id
    id_a = compute_blocker_id("a", "b", "c")
    id_b = compute_blocker_id("c", "b", "a")
    assert id_a != id_b
    # but same call twice is identical
    assert compute_blocker_id("a", "b", "c") == id_a


@pytest.mark.unit
def test_dispatch_claim_json_roundtrip() -> None:
    claim = _make_claim()
    serialized = claim.model_dump_json()
    restored = ModelDispatchClaim.model_validate_json(serialized)
    assert restored == claim


@pytest.mark.unit
def test_claim_ttl_expired() -> None:
    past = datetime(2020, 1, 1, tzinfo=UTC)
    claim = _make_claim(claimed_at=past, ttl_seconds=1)
    assert claim.is_expired() is True

    future_claim = _make_claim(ttl_seconds=3600)
    assert future_claim.is_expired() is False


@pytest.mark.unit
def test_invalid_blocker_id_rejected() -> None:
    with pytest.raises(ValidationError):
        _make_claim(blocker_id="not-a-sha1")

    with pytest.raises(ValidationError):
        # 39 chars — too short
        _make_claim(blocker_id="a" * 39)

    with pytest.raises(ValidationError):
        # uppercase — not valid sha1 hex lowercase
        _make_claim(blocker_id="A" * 40)
