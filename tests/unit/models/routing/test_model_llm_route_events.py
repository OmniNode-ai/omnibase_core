# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for canonical LLM route event DTOs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_routing_error_class import RoutingErrorClass
from omnibase_core.models.routing.model_llm_route_rejected_event import (
    ModelLlmRouteRejectedEvent,
)
from omnibase_core.models.routing.model_llm_route_resolved_event import (
    ModelLlmRouteResolvedEvent,
)
from omnibase_core.models.routing.model_routing_policy import ModelRoutingPolicy
from omnibase_core.models.routing.model_served_model_name import ModelServedModelName
from omnibase_core.models.routing.model_served_model_ref import ModelServedModelRef


def test_resolved_route_event_requires_policy_hash_alias_match() -> None:
    routing_decision_id = uuid4()
    event = ModelLlmRouteResolvedEvent(
        routing_decision_id=routing_decision_id,
        correlation_id="corr-1",
        logical_model_key="coder",
        served_model_id=ModelServedModelRef(
            provider="local", model_id="qwen3-coder-30b"
        ),
        endpoint_ref="LLM_LOCAL_PRIMARY_URL",
        provider="local",
        registry_hash="sha256:registry",
        routing_policy_hash="sha256:policy",
        policy_hash="sha256:policy",
        pricing_manifest_hash="sha256:pricing",
        fallback_reason="",
        used_fallback=False,
        created_at=datetime.now(UTC),
    )

    assert event.policy_hash == event.routing_policy_hash
    assert event.logical_model_key == "coder"
    assert event.routing_decision_id == routing_decision_id
    assert event.model_dump(mode="json")["routing_decision_id"] == str(
        routing_decision_id
    )
    assert event.model_dump(mode="json")["served_model_id"] == {
        "provider": "local",
        "model_id": "qwen3-coder-30b",
    }


def test_resolved_route_event_rejects_mismatched_policy_hash_alias() -> None:
    with pytest.raises(ValidationError, match="policy_hash must equal"):
        ModelLlmRouteResolvedEvent(
            routing_decision_id=uuid4(),
            correlation_id="corr-1",
            logical_model_key="coder",
            served_model_id=ModelServedModelRef(
                provider="local", model_id="qwen3-coder-30b"
            ),
            endpoint_ref="LLM_LOCAL_PRIMARY_URL",
            provider="local",
            registry_hash="sha256:registry",
            routing_policy_hash="sha256:policy",
            policy_hash="sha256:other",
            pricing_manifest_hash="sha256:pricing",
            fallback_reason="",
            used_fallback=False,
            created_at=datetime.now(UTC),
        )


def test_rejected_route_event_carries_failure_classification() -> None:
    event = ModelLlmRouteRejectedEvent(
        routing_decision_id=uuid4(),
        correlation_id="corr-2",
        logical_model_key="coder",
        registry_hash="sha256:registry",
        routing_policy_hash="sha256:policy",
        policy_hash="sha256:policy",
        pricing_manifest_hash="sha256:pricing",
        fallback_reason="primary unavailable",
        failure_class=RoutingErrorClass.FALLBACK_UNAUTHORIZED,
        failure_reason="role is not authorized for fallback",
        created_at=datetime.now(UTC),
    )

    assert event.failure_class is RoutingErrorClass.FALLBACK_UNAUTHORIZED
    assert event.served_model_id is None
    assert event.model_dump(mode="json")["served_model_id"] is None


def test_served_model_ref_rejects_empty_provider_or_model_id() -> None:
    with pytest.raises(ValidationError, match="nonempty"):
        ModelServedModelRef(provider=" ", model_id="qwen3-coder-30b")
    with pytest.raises(ValidationError, match="nonempty"):
        ModelServedModelRef(provider="local", model_id=" ")


def test_served_model_name_is_frozen_and_serializes_as_scalar() -> None:
    name = ModelServedModelName("qwen3-coder-30b")
    assert name.root == "qwen3-coder-30b"
    assert name.model_dump(mode="json") == "qwen3-coder-30b"
    with pytest.raises(ValidationError, match="nonempty"):
        ModelServedModelName(" \t")
    with pytest.raises(ValidationError, match="frozen"):
        name.root = "other"  # type: ignore[misc]


def test_served_model_ref_keeps_model_id_as_nested_scalar() -> None:
    reference = ModelServedModelRef(provider="local", model_id="qwen3-coder-30b")
    assert reference.model_id.root == "qwen3-coder-30b"
    assert reference.model_dump(mode="json") == {
        "provider": "local",
        "model_id": "qwen3-coder-30b",
    }


def test_resolved_route_event_rejects_mismatched_served_model_provider() -> None:
    with pytest.raises(ValidationError, match="must equal event provider"):
        ModelLlmRouteResolvedEvent(
            routing_decision_id=uuid4(),
            correlation_id="corr-1",
            logical_model_key="coder",
            served_model_id=ModelServedModelRef(
                provider="remote", model_id="qwen3-coder-30b"
            ),
            endpoint_ref="LLM_LOCAL_PRIMARY_URL",
            provider="local",
            registry_hash="sha256:registry",
            routing_policy_hash="sha256:policy",
            policy_hash="sha256:policy",
            pricing_manifest_hash="sha256:pricing",
            created_at=datetime.now(UTC),
        )


def test_rejected_route_event_allows_only_null_or_provider_qualified_model_reference() -> (
    None
):
    routing_decision_id = uuid4()
    event = ModelLlmRouteRejectedEvent(
        routing_decision_id=routing_decision_id,
        correlation_id="corr-1",
        logical_model_key="coder",
        served_model_id=ModelServedModelRef(
            provider="local", model_id="qwen3-coder-30b"
        ),
        endpoint_ref="LLM_LOCAL_PRIMARY_URL",
        provider="local",
        registry_hash="sha256:registry",
        routing_policy_hash="sha256:policy",
        policy_hash="sha256:policy",
        pricing_manifest_hash="sha256:pricing",
        failure_class=RoutingErrorClass.NO_ELIGIBLE_MODEL,
        failure_reason="none",
        created_at=datetime.now(UTC),
    )

    assert isinstance(event.routing_decision_id, UUID)
    assert event.served_model_id == ModelServedModelRef(
        provider="local", model_id="qwen3-coder-30b"
    )


def test_model_routing_policy_requires_fallback_when_roles_declared() -> None:
    with pytest.raises(ValidationError, match="fallback must be set"):
        ModelRoutingPolicy(primary="qwen3-coder-30b", fallback_allowed_roles=["fixer"])
