# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for the shared fan-out publish-topic resolver (OMN-14403 §6ii).

Proves the four load-bearing rules of the shared resolver both runtimes call:
exact-type resolution, fail-closed on unmapped, carrier rejection, and boot
injectivity. This is the parity contract — the same behavior the Kafka half must
observe once reconciled to this module.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.runtime_fanout_resolver import (
    assert_published_events_injective,
    derive_event_type_from_topic,
    is_fanout_sequence,
    normalize_fanout_elements,
    resolve_fanout_emissions,
    resolve_fanout_topics,
    resolve_published_topic,
)


class ModelAlpha(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int = 0


class ModelBeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int = 0


class ModelGamma(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int = 0


class ModelWithEmbeddedTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = "onex.evt.smuggled.v1"


# A class named exactly like the routing carrier the resolver must reject. The
# resolver keys on ``type(e).__name__``, so a local stand-in is sufficient and
# avoids constructing the generic real envelope.
class ModelEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: int = 0


_PUBLISHED = {
    "Alpha": "onex.evt.alpha.v1",
    "Beta": "onex.evt.beta.v1",
}


class TestIsFanoutSequence:
    def test_tuple_of_models_is_fanout(self) -> None:
        assert is_fanout_sequence((ModelAlpha(), ModelBeta())) is True

    def test_list_of_models_is_fanout(self) -> None:
        assert is_fanout_sequence([ModelAlpha()]) is True

    def test_single_model_is_not_fanout(self) -> None:
        assert is_fanout_sequence(ModelAlpha()) is False

    def test_str_is_not_fanout(self) -> None:
        assert is_fanout_sequence("onex.evt.x") is False

    def test_bytes_is_not_fanout(self) -> None:
        assert is_fanout_sequence(b"payload") is False

    def test_dict_is_not_fanout(self) -> None:
        assert is_fanout_sequence({"a": 1}) is False

    def test_none_is_not_fanout(self) -> None:
        assert is_fanout_sequence(None) is False


class TestResolvePublishedTopic:
    def test_resolves_by_short_name(self) -> None:
        assert resolve_published_topic(_PUBLISHED, ModelAlpha()) == "onex.evt.alpha.v1"

    def test_resolves_full_class_name_spelling(self) -> None:
        # A map keyed by the full class name (Model prefix present) still resolves.
        published = {"ModelAlpha": "onex.evt.alpha.v1"}
        assert resolve_published_topic(published, ModelAlpha()) == "onex.evt.alpha.v1"

    def test_unmapped_class_fails_closed(self) -> None:
        # Gamma is not in the map -> raise, never fall back to a single topic.
        with pytest.raises(ModelOnexError, match="not declared in the contract"):
            resolve_published_topic(_PUBLISHED, ModelGamma())


class TestNormalizeFanoutElements:
    def test_preserves_order_and_returns_models(self) -> None:
        a, b = ModelAlpha(value=1), ModelBeta(value=2)
        assert normalize_fanout_elements([a, b]) == [a, b]

    def test_non_model_element_raises_never_filters(self) -> None:
        with pytest.raises(ModelOnexError, match="not a BaseModel"):
            normalize_fanout_elements([ModelAlpha(), "not-a-model"])

    def test_rejects_routing_carrier(self) -> None:
        with pytest.raises(ModelOnexError, match="routing carrier"):
            normalize_fanout_elements([ModelEventEnvelope()])

    def test_rejects_embedded_topic(self) -> None:
        with pytest.raises(ModelOnexError, match="embedded topic"):
            normalize_fanout_elements([ModelWithEmbeddedTopic()])


class TestResolveFanoutTopics:
    def test_ordered_topic_payload_pairs(self) -> None:
        a, b = ModelAlpha(value=1), ModelBeta(value=2)
        resolved = resolve_fanout_topics(_PUBLISHED, [a, b])
        assert resolved == [("onex.evt.alpha.v1", a), ("onex.evt.beta.v1", b)]

    def test_unmapped_in_sequence_fails_closed(self) -> None:
        with pytest.raises(ModelOnexError, match="not declared in the contract"):
            resolve_fanout_topics(_PUBLISHED, [ModelAlpha(), ModelGamma()])


class TestAssertPublishedEventsInjective:
    def test_injective_map_passes(self) -> None:
        assert_published_events_injective(_PUBLISHED, context="test")

    def test_redundant_short_and_full_spelling_same_topic_passes(self) -> None:
        published = {"Alpha": "onex.evt.alpha.v1", "ModelAlpha": "onex.evt.alpha.v1"}
        assert_published_events_injective(published, context="test")

    def test_same_class_two_topics_fails(self) -> None:
        # Short and full spelling of the SAME class disagree on topic -> ambiguous.
        published = {"Alpha": "onex.evt.alpha.v1", "ModelAlpha": "onex.evt.other.v1"}
        with pytest.raises(ModelOnexError, match="two topics"):
            assert_published_events_injective(published, context="test")

    def test_two_classes_one_topic_fails(self) -> None:
        published = {"Alpha": "onex.evt.shared.v1", "Beta": "onex.evt.shared.v1"}
        with pytest.raises(ModelOnexError, match="injective"):
            assert_published_events_injective(published, context="test")


# Canonical 5-segment ONEX topics so an event_type is derivable (OMN-14743).
_PUBLISHED_CANONICAL = {
    "Alpha": "onex.evt.omni.alpha.v1",
    "Beta": "onex.cmd.omni.beta.v1",
}


class TestDeriveEventTypeFromTopic:
    def test_canonical_topic_derives_producer_event_name(self) -> None:
        assert (
            derive_event_type_from_topic(
                "onex.cmd.omnibase-infra.delegation-routing-request.v1"
            )
            == "omnibase-infra.delegation-routing-request"
        )

    def test_evt_topic_derives(self) -> None:
        assert derive_event_type_from_topic("onex.evt.omni.alpha.v1") == "omni.alpha"

    def test_four_segment_topic_yields_none(self) -> None:
        # Missing the {event-name} segment -> not derivable.
        assert derive_event_type_from_topic("onex.evt.alpha.v1") is None

    def test_non_onex_prefix_yields_none(self) -> None:
        assert derive_event_type_from_topic("kafka.raw.a.b.c") is None


class TestResolveFanoutEmissions:
    def test_returns_topic_event_type_payload_triples_in_order(self) -> None:
        elements = [ModelAlpha(value=1), ModelBeta(value=2)]
        emissions = resolve_fanout_emissions(_PUBLISHED_CANONICAL, elements)
        assert [(t, et, type(p).__name__) for t, et, p in emissions] == [
            ("onex.evt.omni.alpha.v1", "omni.alpha", "ModelAlpha"),
            ("onex.cmd.omni.beta.v1", "omni.beta", "ModelBeta"),
        ]

    def test_fails_closed_when_topic_yields_no_event_type(self) -> None:
        # A 4-segment topic resolves fine as a topic but yields no event_type ->
        # emitting it would produce a null-event_type envelope the type-scoped
        # dispatcher drops, so the emit boundary must raise instead.
        published = {"Alpha": "onex.evt.alpha.v1"}
        with pytest.raises(ModelOnexError, match="event_type"):
            resolve_fanout_emissions(published, [ModelAlpha(value=1)])

    def test_unmapped_class_still_fails_closed(self) -> None:
        with pytest.raises(ModelOnexError):
            resolve_fanout_emissions(_PUBLISHED_CANONICAL, [ModelGamma(value=1)])
