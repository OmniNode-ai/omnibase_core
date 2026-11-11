# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for the delegation routing order models (OMN-23637)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_delegation_routing_order_refusal import (
    EnumDelegationRoutingOrderRefusal,
)
from omnibase_core.enums.enum_delegation_routing_order_rung_kind import (
    EnumDelegationRoutingOrderRungKind,
)
from omnibase_core.models.delegation.model_delegation_routing_order_answer import (
    ModelDelegationRoutingOrderAnswer,
)
from omnibase_core.models.delegation.model_delegation_routing_order_request import (
    ModelDelegationRoutingOrderRequest,
)
from omnibase_core.models.delegation.model_delegation_routing_order_rung import (
    ModelDelegationRoutingOrderRung,
)


def _ladder_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "position": 0,
        "tier": "primary",
        "kind": EnumDelegationRoutingOrderRungKind.LADDER,
        "backend_ids": ("backend-1", "backend-2"),
        "harness": None,
        "model_name": "model-a",
        "max_retries": 2,
        "attempts": 3,
        "refusals": ("overlay_unbound",),
    }
    kwargs.update(overrides)
    return kwargs


def _harness_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "position": 1,
        "tier": "fallback",
        "kind": EnumDelegationRoutingOrderRungKind.HARNESS,
        "backend_ids": ("harness-backend",),
        "harness": "harness-x",
        "model_name": None,
        "max_retries": None,
        "attempts": 1,
        "refusals": (),
    }
    kwargs.update(overrides)
    return kwargs


def _ladder_rung(**overrides: object) -> ModelDelegationRoutingOrderRung:
    kwargs = _ladder_kwargs(**overrides)
    return ModelDelegationRoutingOrderRung.model_validate(kwargs)


def _harness_rung(**overrides: object) -> ModelDelegationRoutingOrderRung:
    kwargs = _harness_kwargs(**overrides)
    return ModelDelegationRoutingOrderRung.model_validate(kwargs)


@pytest.mark.unit
class TestModelDelegationRoutingOrderRequest:
    def test_minimal_instantiation(self) -> None:
        req = ModelDelegationRoutingOrderRequest(
            task_class="compute",
            tenant_slug="tenant-1",
            surface="cli",
            pin_lifted=True,
        )
        assert req.task_class == "compute"
        assert req.tenant_slug == "tenant-1"
        assert req.surface == "cli"
        assert req.pin_lifted is True

    def test_tenant_slug_may_be_none(self) -> None:
        req = ModelDelegationRoutingOrderRequest(
            task_class="compute",
            tenant_slug=None,
            surface="cli",
            pin_lifted=False,
        )
        assert req.tenant_slug is None

    def test_frozen(self) -> None:
        req = ModelDelegationRoutingOrderRequest(
            task_class="compute",
            tenant_slug="tenant-1",
            surface="cli",
            pin_lifted=False,
        )
        with pytest.raises((TypeError, ValidationError)):
            setattr(req, "surface", "web")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationRoutingOrderRequest(
                task_class="compute",
                tenant_slug="tenant-1",
                surface="cli",
                pin_lifted=False,
                unknown_field="boom",
            )


@pytest.mark.unit
class TestModelDelegationRoutingOrderRung:
    def test_valid_ladder_rung(self) -> None:
        rung = _ladder_rung()
        assert rung.attempts == 3
        assert rung.max_retries == 2
        assert rung.kind is EnumDelegationRoutingOrderRungKind.LADDER

    def test_valid_harness_rung(self) -> None:
        rung = _harness_rung()
        assert rung.attempts == 1
        assert rung.max_retries is None
        assert rung.kind is EnumDelegationRoutingOrderRungKind.HARNESS

    def test_ladder_attempts_equal_to_max_retries_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _ladder_rung(attempts=2)

    def test_harness_rung_with_max_retries_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _harness_rung(max_retries=1)


@pytest.mark.unit
class TestModelDelegationRoutingOrderAnswer:
    def test_ok_answer_requires_rungs(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationRoutingOrderAnswer(
                ok=True,
                task_class="compute",
                rungs=(),
                refusal=None,
                detail="plan",
            )

    def test_refused_answer_requires_refusal(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationRoutingOrderAnswer(
                ok=False,
                task_class="compute",
                rungs=(),
                refusal=None,
                detail="overlay not bound",
            )

    def test_refused_answer_shape(self) -> None:
        answer = ModelDelegationRoutingOrderAnswer(
            ok=False,
            task_class="compute",
            rungs=(),
            refusal=EnumDelegationRoutingOrderRefusal.OVERLAY_UNBOUND,
            detail="overlay not bound",
        )
        assert answer.refusal is EnumDelegationRoutingOrderRefusal.OVERLAY_UNBOUND

    def test_ok_answer_shape(self) -> None:
        answer = ModelDelegationRoutingOrderAnswer(
            ok=True,
            task_class="compute",
            rungs=(_ladder_rung(),),
            refusal=None,
            detail="plan",
        )
        assert answer.ok is True
        assert len(answer.rungs) == 1
