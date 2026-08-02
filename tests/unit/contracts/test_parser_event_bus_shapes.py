# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for event-bus contract parser supporting classic and nested shapes."""

import pytest

from omnibase_core.contracts.contract_parser_event_bus import parse_event_bus
from omnibase_core.errors.error_event_bus_contract_shape import (
    EventBusContractShapeError,
)
from omnibase_core.models.contracts.model_event_bus_subscription import (
    ModelEventBusSubscription,
)


@pytest.mark.unit
def test_classic_subscribe_topics_shape_parses() -> None:
    contract = {"event_bus": {"subscribe_topics": ["onex.evt.foo.v1"]}}
    parsed = parse_event_bus(contract)
    assert parsed.subscriptions == [ModelEventBusSubscription(topic="onex.evt.foo.v1")]


@pytest.mark.unit
def test_nested_subscribe_topic_shape_parses() -> None:
    contract = {"event_bus": {"subscribe": [{"topic": "onex.evt.bar.v1"}]}}
    parsed = parse_event_bus(contract)
    assert parsed.subscriptions == [
        ModelEventBusSubscription(topic="onex.evt.bar.v1"),
    ]


@pytest.mark.unit
def test_nested_subscribe_consumer_group_is_rejected() -> None:
    """OMN-15639: the field was parsed and never read; it is now a loud failure.

    Accepting it would restore the ad-hoc naming surface that let a contract mint a
    consumer group no MSK IAM pattern authorizes.
    """
    contract = {
        "event_bus": {
            "subscribe": [{"topic": "onex.evt.bar.v1", "consumer_group": "g1"}],
        },
    }
    with pytest.raises(EventBusContractShapeError, match="consumer_group"):
        parse_event_bus(contract)


@pytest.mark.unit
def test_unknown_shape_fails_loudly() -> None:
    contract = {"event_bus": {"weird_key": "x"}}
    with pytest.raises(EventBusContractShapeError):
        parse_event_bus(contract)


@pytest.mark.unit
def test_missing_event_bus_returns_empty_subscriptions() -> None:
    parsed = parse_event_bus({})
    assert parsed.subscriptions == []


@pytest.mark.unit
def test_classic_and_nested_shapes_merge() -> None:
    contract = {
        "event_bus": {
            "subscribe_topics": ["onex.evt.foo.v1"],
            "subscribe": [{"topic": "onex.evt.bar.v1"}],
        },
    }
    parsed = parse_event_bus(contract)
    assert parsed.subscriptions == [
        ModelEventBusSubscription(topic="onex.evt.foo.v1"),
        ModelEventBusSubscription(topic="onex.evt.bar.v1"),
    ]


@pytest.mark.unit
def test_nested_subscribe_unknown_key_is_rejected() -> None:
    """Regression: unknown nested keys were silently dropped.

    The subscription model is built from ``topic`` alone, so an unrecognized key never
    reached ``ModelEventBusSubscription``'s ``extra="forbid"`` — it was discarded here.
    A silent subscription-shape drop is precisely what this parser exists to prevent.
    """
    contract = {
        "event_bus": {
            "subscribe": [{"topic": "onex.evt.bar.v1", "subscrbe_group": "typo"}],
        },
    }
    with pytest.raises(EventBusContractShapeError, match="subscrbe_group"):
        parse_event_bus(contract)


@pytest.mark.unit
def test_nested_shape_missing_topic_field_raises() -> None:
    contract = {"event_bus": {"subscribe": [{"not_a_topic": "x"}]}}
    with pytest.raises(EventBusContractShapeError, match="topic"):
        parse_event_bus(contract)


@pytest.mark.unit
def test_event_bus_not_a_mapping_raises() -> None:
    contract = {"event_bus": ["onex.evt.foo.v1"]}
    with pytest.raises(EventBusContractShapeError):
        parse_event_bus(contract)


@pytest.mark.unit
def test_unknown_key_alongside_known_shape_raises() -> None:
    contract = {
        "event_bus": {
            "subscribe_topics": ["onex.evt.foo.v1"],
            "subscrbe_topics": ["onex.evt.typo.v1"],
        },
    }
    with pytest.raises(EventBusContractShapeError, match="subscrbe_topics"):
        parse_event_bus(contract)


@pytest.mark.unit
def test_unknown_key_alongside_nested_shape_raises() -> None:
    contract = {
        "event_bus": {
            "subscribe": [{"topic": "onex.evt.bar.v1"}],
            "subscrbe": [{"topic": "onex.evt.typo.v1"}],
        },
    }
    with pytest.raises(EventBusContractShapeError, match="subscrbe"):
        parse_event_bus(contract)
