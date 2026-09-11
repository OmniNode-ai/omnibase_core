# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The wire contract for which credential served a delegation (OMN-18196).

Axiom 9 forbids a customer route binding a house credential. A model name
cannot witness that -- the same model id is reachable on a customer's own key
and on the platform's -- so the fact needs a field of its own, produced by the
boundary that resolved the credential and copied unchanged by everything
downstream.

These tests pin the CONTRACT: the three values, the defaulting that lets an
older producer's terminal still parse, and the deliberate decision NOT to pair
this field with route/provider.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_credential_source import EnumCredentialSource
from omnibase_core.models.delegation.wire import (
    ModelDelegationResult,
)
from omnibase_core.models.delegation.wire.model_orchestrator_intents import (
    ModelInferenceResponseData,
)


def _result(**kwargs: object) -> ModelDelegationResult:
    defaults: dict[str, object] = {
        "correlation_id": uuid4(),
        "task_type": "test",
        "model_used": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "endpoint_url": "https://openrouter.ai/api/v1/chat/completions",
        "content": "ok",
        "quality_passed": True,
        "quality_score": 1.0,
        "latency_ms": 12,
        "fallback_to_claude": False,
    }
    defaults.update(kwargs)
    return ModelDelegationResult(**defaults)  # type: ignore[arg-type]


def _response(**kwargs: object) -> ModelInferenceResponseData:
    defaults: dict[str, object] = {
        "correlation_id": uuid4(),
        "content": "ok",
        "model_used": "nvidia/nemotron-3-ultra-550b-a55b:free",
    }
    defaults.update(kwargs)
    return ModelInferenceResponseData(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestTheEnum:
    def test_it_names_exactly_the_three_outcomes_a_call_can_have(self) -> None:
        assert {member.value for member in EnumCredentialSource} == {
            "customer_key",
            "house",
            "none",
        }

    def test_the_values_are_the_wire_strings(self) -> None:
        """Serialised terminals carry these strings; the gateway matches on them."""
        assert EnumCredentialSource.CUSTOMER_KEY == "customer_key"
        assert EnumCredentialSource.HOUSE == "house"
        assert EnumCredentialSource.NONE == "none"


@pytest.mark.unit
class TestTheTerminalCarriesIt:
    @pytest.mark.parametrize("source", list(EnumCredentialSource))
    def test_every_value_round_trips_on_the_wire(
        self, source: EnumCredentialSource
    ) -> None:
        dumped = _result(credential_source=source).model_dump(mode="json")
        assert dumped["credential_source"] == source.value
        assert ModelDelegationResult.model_validate(dumped).credential_source is source

    def test_a_terminal_from_a_producer_that_predates_the_field_still_parses(
        self,
    ) -> None:
        """A consumer must not turn a missing explanation into no terminal."""
        assert _result().credential_source is None

    def test_absent_is_omitted_rather_than_serialised_as_null(self) -> None:
        """Absent means the producer made no claim, and says so by saying nothing."""
        assert "credential_source" not in _result().model_dump(mode="json")

    def test_an_unrecognised_credential_class_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _result(credential_source="borrowed")

    def test_it_is_not_paired_with_route_and_provider(self) -> None:
        """A refused call has a credential source and no route at all.

        ``route``/``provider`` validate as a pair, and it would be easy to
        assume this field joins them. It must not: the case this field exists
        to record most sharply -- a call that reached no provider because no
        credential was available -- has a credential source of ``none`` and
        nothing to say about a route.
        """
        result = _result(credential_source=EnumCredentialSource.NONE)
        assert result.credential_source is EnumCredentialSource.NONE
        assert result.route is None
        assert result.provider is None


@pytest.mark.unit
class TestTheInferenceResponseCarriesIt:
    """The response is where the fact enters the system, first-hand."""

    @pytest.mark.parametrize("source", list(EnumCredentialSource))
    def test_every_value_round_trips(self, source: EnumCredentialSource) -> None:
        dumped = _response(credential_source=source).model_dump(mode="json")
        assert dumped["credential_source"] == source.value
        assert (
            ModelInferenceResponseData.model_validate(dumped).credential_source
            is source
        )

    def test_a_response_from_an_older_effect_still_parses(self) -> None:
        assert _response().credential_source is None

    def test_an_unrecognised_credential_class_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _response(credential_source="borrowed")
