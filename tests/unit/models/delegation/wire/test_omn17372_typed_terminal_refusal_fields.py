# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The delegation terminal carries its refusal TYPED, not spelled into prose.

OMN-17372 AC2. A keyless customer's cloud delegation is refused by
``omnimarket``'s ``refuse_keyless_customer_on_cloud`` before the house ladder
is ever loaded, and the consume boundary terminalizes that refusal with a
``failure_class`` (``CustomerKeyRefusedError``) and a canonical ``failure_code``
(``ONEX_MARKET_CUSTOMER_PROVIDER_KEY_ABSENT``) already in hand
(``omnibase_infra.runtime.boundary_failure_terminal.ModelBoundaryFailureTerminal``).

Until this change the delegation terminal DTO had nowhere to put either of
them. The orchestrator flattened the pair into one ``terminal_failure_reason``
string, ``f"{failure_class}: {failure_code}"``, so every downstream reader that
wanted the code back had to split a string on ``": "`` -- a shape with no
contract behind it. ``GET /v1/workflows/{id}/status`` did not even try: it
carried no failure field at all, and a refused run read as
``{"status": "failed"}`` with a null model and zero tokens, indistinguishable
from an outage.

These three fields are the typed halves. The invariants below are the point of
adding them rather than three more free-text strings:

* a SUCCESS may not carry any of them -- a completed delegation that names a
  failure code is contradictory terminal truth, the same class of defect
  ``validate_structured_terminal_evidence`` already rejects for the quality
  bar;
* a FAILED terminal must name its ``failure_class`` -- "something failed" with
  no attribution is the ``dispatch_timeout`` answer OMN-16812 was written to
  delete, and every failure path through the orchestrator's single
  ``_emit_terminal`` builder has a class in hand;
* ``failure_code`` may be absent, but only ALONGSIDE a class. Not every
  failure carries a canonical ONEX code (a quality-gate rejection does not),
  and inventing one would be worse than reporting its absence -- the same
  posture ``ModelBoundaryFailureTerminal.failure_code`` already documents. A
  code with no class, though, is a producer bug: the code is the more specific
  half of a pair whose less specific half is always derivable.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import (
    ModelDelegationCompleted,
    ModelDelegationFailed,
    ModelDelegationResult,
)

_ONEX_CODE = "ONEX_MARKET_CUSTOMER_PROVIDER_KEY_ABSENT"
_FAILURE_CLASS = "CustomerKeyRefusedError"
_REMEDIATION = "Register a provider key for this tenant and retry."


def _terminal_kwargs(**overrides: Any) -> dict[str, Any]:
    """A minimally valid FAILED delegation terminal, plus overrides."""
    base: dict[str, Any] = {
        "correlation_id": uuid.uuid4(),
        "task_type": "summarization",
        "model_used": "none",
        "endpoint_url": "none",
        "content": "",
        "quality_passed": False,
        "quality_score": 0.0,
        "latency_ms": 12,
        "fallback_to_claude": False,
    }
    base.update(overrides)
    return base


class TestRefusalFieldsAreCarriedTyped:
    """The three fields exist and round-trip on the wire shape."""

    def test_failed_terminal_carries_class_code_and_remediation(self) -> None:
        result = ModelDelegationFailed(
            **_terminal_kwargs(
                failure_class=_FAILURE_CLASS,
                failure_code=_ONEX_CODE,
                remediation=_REMEDIATION,
                failure_reason=(
                    f"[{_ONEX_CODE}] delegation.customer_provider_key.absent: "
                    f"no provider key is registered for this tenant. {_REMEDIATION}"
                ),
            )
        )

        assert result.failure_class == _FAILURE_CLASS
        assert result.failure_code == _ONEX_CODE
        assert result.remediation == _REMEDIATION

        # The typed halves survive a JSON round trip -- this DTO crosses Kafka.
        wire = result.model_dump(mode="json")
        assert wire["failure_code"] == _ONEX_CODE
        assert wire["failure_class"] == _FAILURE_CLASS
        assert wire["remediation"] == _REMEDIATION
        assert ModelDelegationFailed.model_validate(wire).failure_code == _ONEX_CODE

    def test_unrelated_failure_class_keeps_its_own_attribution(self) -> None:
        """A different failure class is carried as itself, not collapsed."""
        result = ModelDelegationFailed(
            **_terminal_kwargs(
                failure_class="ProtocolConfigurationError",
                failure_code="ONEX_CORE_041_INVALID_CONFIGURATION",
                failure_reason="no tier has a configured endpoint",
            )
        )
        assert result.failure_class == "ProtocolConfigurationError"
        assert result.failure_code == "ONEX_CORE_041_INVALID_CONFIGURATION"
        # Absent remediation is absent, never a fabricated sentence.
        assert result.remediation is None

    def test_failure_code_may_be_absent_when_the_failure_carried_none(self) -> None:
        result = ModelDelegationFailed(
            **_terminal_kwargs(
                failure_class="QualityGateRejectionError",
                failure_reason="quality bar not met",
            )
        )
        assert result.failure_class == "QualityGateRejectionError"
        assert result.failure_code is None


class TestSuccessMustNotCarryAFailure:
    """A completed delegation naming a failure is contradictory, not tolerable."""

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("failure_class", _FAILURE_CLASS),
            ("failure_code", _ONEX_CODE),
            ("remediation", _REMEDIATION),
        ],
    )
    def test_quality_passed_result_rejects_each_failure_field(
        self, field: str, value: str
    ) -> None:
        with pytest.raises(ValidationError, match="cannot carry"):
            ModelDelegationResult(
                **_terminal_kwargs(
                    quality_passed=True, quality_score=0.9, **{field: value}
                )
            )

    def test_completed_terminal_rejects_a_failure_code(self) -> None:
        with pytest.raises(ValidationError, match="cannot carry"):
            ModelDelegationCompleted(
                **_terminal_kwargs(
                    quality_passed=True,
                    quality_score=0.9,
                    failure_code=_ONEX_CODE,
                    failure_class=_FAILURE_CLASS,
                )
            )

    def test_completed_terminal_with_no_failure_fields_is_accepted(self) -> None:
        completed = ModelDelegationCompleted(
            **_terminal_kwargs(quality_passed=True, quality_score=0.9)
        )
        assert completed.failure_code is None
        assert completed.failure_class is None
        assert completed.remediation is None


class TestACodeNeverTravelsWithoutItsClass:
    """The pairing invariant -- and the deliberate limit on how far it goes.

    The positive requirement ("a FAILED terminal names its class") is enforced
    at the PRODUCER, not here. omnimarket's ``_emit_terminal`` is the single
    construction site for every delegation terminal, and its own test suite
    pins that every failure path supplies a ``failure_class``.

    It is deliberately NOT a validator on ``ModelDelegationFailed``, because
    this DTO and its producer version-skew: a released core carrying such a
    validator, consumed by an omnimarket that has not yet learned to populate
    the field, would reject EVERY delegation failure terminal at construction
    -- no terminal published, the orchestrator FSM parked forever, and
    ``gateway_workflows.status`` stuck at ``published``. That is precisely the
    silent-stall class OMN-17397 and OMN-17445 were written to close, and a
    validator whose failure mode is re-opening them is not a safety property.
    The invariants that DO live here are the ones no producer can be broken
    by, because nothing sets these fields today.
    """

    @pytest.mark.parametrize("field", ["failure_code", "remediation"])
    def test_a_failure_field_without_a_class_is_rejected(self, field: str) -> None:
        """A code (or a remediation) is the specific half of a pair."""
        value = _ONEX_CODE if field == "failure_code" else _REMEDIATION
        with pytest.raises(ValidationError, match="failure_class"):
            ModelDelegationResult(**_terminal_kwargs(**{field: value}))

    def test_blank_failure_class_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="failure_class"):
            ModelDelegationResult(**_terminal_kwargs(failure_class="   "))

    def test_a_class_alone_is_accepted(self) -> None:
        """Attribution without a canonical code is the common failure shape."""
        result = ModelDelegationFailed(
            **_terminal_kwargs(failure_class="QualityGateRejectionError")
        )
        assert result.failure_class == "QualityGateRejectionError"
        assert result.failure_code is None
        assert result.remediation is None

    def test_a_failure_terminal_with_no_attribution_still_constructs(self) -> None:
        """Version skew: an un-migrated producer is not broken by this change."""
        result = ModelDelegationFailed(**_terminal_kwargs())
        assert result.failure_class is None
        assert result.failure_code is None
