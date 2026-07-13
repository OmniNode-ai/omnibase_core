# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Cross-boundary regression tests for the canonical node introspection event.

OMN-14490: ``ModelNodeIntrospectionEvent`` is the single canonical wire model for
the ``node-introspection.v1`` topic, graduated from ``omnibase_infra`` into
``omnibase_core`` so the producer (infra) and every consumer (e.g. omnimarket's
``node_projection_registration``) share ONE definition.

The defect this file guards against: a consumer that re-declares a *slim* local
copy with ``extra="ignore"`` silently DROPS the rich producer fields
(``endpoints`` / ``declared_capabilities`` / ``discovered_capabilities`` /
``contract_capabilities`` / ``current_state``). These tests prove the canonical
model (a) round-trips those fields losslessly across the JSON wire boundary and
(b) fails LOUD (``extra="forbid"``) on an unmodeled field instead of dropping it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumIntrospectionReason, EnumNodeKind
from omnibase_core.models.capabilities import ModelContractCapabilities
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.registration import (
    ModelDiscoveredCapabilities,
    ModelEventBusTopicEntry,
    ModelNodeCapabilities,
    ModelNodeEventBusConfig,
    ModelNodeIntrospectionEvent,
    ModelNodeMetadata,
)

# The rich producer fields that a slim ``extra="ignore"`` consumer silently drops.
_RICH_FIELDS = (
    "endpoints",
    "declared_capabilities",
    "discovered_capabilities",
    "contract_capabilities",
    "current_state",
)


def _rich_event() -> ModelNodeIntrospectionEvent:
    """A fully-populated event mirroring a real producer broadcast.

    Every rich field carries a NON-default value so a silent drop is detectable.
    """
    return ModelNodeIntrospectionEvent(
        node_id=uuid4(),
        node_name="node_delegation_orchestrator",
        node_type=EnumNodeKind.ORCHESTRATOR,
        node_version=ModelSemVer(major=1, minor=2, patch=3),
        correlation_id=uuid4(),
        timestamp=datetime.now(UTC),
        reason=EnumIntrospectionReason.STARTUP,
        endpoints={
            "api": "http://localhost:8085",
            "grpc": "grpc://localhost:9090",
        },
        current_state="READY",
        declared_capabilities=ModelNodeCapabilities(postgres=True, write=True),
        discovered_capabilities=ModelDiscoveredCapabilities(
            operations=("execute", "handle"),
            has_fsm=True,
        ),
        contract_capabilities=ModelContractCapabilities(
            contract_type="ORCHESTRATOR_GENERIC",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            intent_types=["delegate.request"],
        ),
        metadata=ModelNodeMetadata(),
        event_bus=ModelNodeEventBusConfig(
            subscribe_topics=[ModelEventBusTopicEntry(topic="onex.evt.in.v1")],
            publish_topics=[ModelEventBusTopicEntry(topic="onex.evt.out.v1")],
        ),
    )


def test_rich_fields_survive_the_json_wire_boundary() -> None:
    """The exact fields the slim consumer dropped must round-trip losslessly."""
    event = _rich_event()

    wire = event.model_dump(mode="json")
    restored = ModelNodeIntrospectionEvent.model_validate(wire)

    assert restored == event, "round-trip mutated the event"

    # Each rich field is present in the wire payload AND non-default after restore.
    for field in _RICH_FIELDS:
        assert field in wire, f"producer field {field!r} missing from wire payload"
    assert restored.endpoints == {
        "api": "http://localhost:8085",
        "grpc": "grpc://localhost:9090",
    }
    assert restored.current_state == "READY"
    assert restored.declared_capabilities.postgres is True
    assert restored.declared_capabilities.write is True
    assert restored.discovered_capabilities.operations == ("execute", "handle")
    assert restored.discovered_capabilities.has_fsm is True
    assert restored.contract_capabilities is not None
    assert restored.event_bus is not None
    assert restored.event_bus.subscribe_topic_strings == ["onex.evt.in.v1"]


def test_extra_forbid_fails_loud_instead_of_silent_drop() -> None:
    """An unmodeled wire field must RAISE, not be silently ignored.

    ``extra="ignore"`` (the slim consumer's config) is exactly what made
    OMN-14490 a silent data loss. The canonical model uses ``extra="forbid"``.
    """
    wire = _rich_event().model_dump(mode="json")
    wire["unexpected_producer_field"] = {"added": "by a newer producer"}

    with pytest.raises(ValidationError):
        ModelNodeIntrospectionEvent.model_validate(wire)


def test_naive_timestamp_is_rejected() -> None:
    """The timezone-aware validator is wired to the canonical core utility."""
    with pytest.raises(ValidationError):
        ModelNodeIntrospectionEvent(
            node_id=uuid4(),
            node_type=EnumNodeKind.EFFECT,
            correlation_id=uuid4(),
            timestamp=datetime.now(),
        )


def test_malformed_endpoint_url_is_rejected() -> None:
    """The endpoint-URL validator is wired to the canonical core utility."""
    with pytest.raises(ValidationError):
        ModelNodeIntrospectionEvent(
            node_id=uuid4(),
            node_type=EnumNodeKind.EFFECT,
            correlation_id=uuid4(),
            timestamp=datetime.now(UTC),
            endpoints={"api": "localhost:8085"},  # missing scheme
        )
