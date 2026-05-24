# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for canonical LLM route event DTOs."""

from __future__ import annotations

from datetime import UTC, datetime

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


def test_resolved_route_event_requires_policy_hash_alias_match() -> None:
    event = ModelLlmRouteResolvedEvent(
        routing_decision_id="decision-1",
        correlation_id="corr-1",
        logical_model_key="coder",
        served_model_id="qwen3-coder-30b",
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


def test_resolved_route_event_rejects_mismatched_policy_hash_alias() -> None:
    with pytest.raises(ValidationError, match="policy_hash must equal"):
        ModelLlmRouteResolvedEvent(
            routing_decision_id="decision-1",
            correlation_id="corr-1",
            logical_model_key="coder",
            served_model_id="qwen3-coder-30b",
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
        routing_decision_id="decision-2",
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
    assert event.served_model_id == ""


def test_model_routing_policy_requires_fallback_when_roles_declared() -> None:
    with pytest.raises(ValidationError, match="fallback must be set"):
        ModelRoutingPolicy(primary="qwen3-coder-30b", fallback_allowed_roles=["fixer"])
