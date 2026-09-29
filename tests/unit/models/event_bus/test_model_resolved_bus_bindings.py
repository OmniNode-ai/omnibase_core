# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract tests for resolved bus bindings and group describe operations."""

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums import EnumBusBindingDirection
from omnibase_core.models.event_bus import (
    ModelBusBinding,
    ModelBusGroupDescribe,
    ModelResolvedBusBindings,
)

pytestmark = pytest.mark.unit


def test_valid_round_trip() -> None:
    resolved = ModelResolvedBusBindings(
        principal="service-reader",
        bindings=(
            ModelBusBinding(
                broker="events",
                physical_topic="tenant.orders",
                direction=EnumBusBindingDirection.CONSUME,
                consumer_group="order-readers",
            ),
            ModelBusBinding(
                broker="events",
                physical_topic="tenant.results",
                direction=EnumBusBindingDirection.PRODUCE,
            ),
        ),
        described_groups=(ModelBusGroupDescribe(broker="events", group="readers"),),
    )

    assert (
        ModelResolvedBusBindings.model_validate_json(resolved.model_dump_json())
        == resolved
    )
    assert resolved.model_dump(mode="json")["bindings"][0]["direction"] == "consume"
    assert resolved.model_dump(mode="json")["bindings"][1]["direction"] == "produce"
    assert isinstance(EnumBusBindingDirection.CONSUME, str)


@pytest.mark.parametrize("group", [None, ""])
def test_consume_requires_nonempty_group(group: str | None) -> None:
    with pytest.raises(ValidationError, match="consumer_group"):
        ModelBusBinding(
            broker="events",
            physical_topic="tenant.orders",
            direction=EnumBusBindingDirection.CONSUME,
            consumer_group=group,
        )


def test_consume_without_group_refused() -> None:
    with pytest.raises(ValidationError, match="consumer_group"):
        ModelBusBinding.model_validate(
            {
                "broker": "events",
                "physical_topic": "tenant.orders",
                "direction": "consume",
            }
        )


@pytest.mark.parametrize("group", ["readers", ""])
def test_produce_forbids_group(group: str) -> None:
    with pytest.raises(ValidationError, match="consumer_group"):
        ModelBusBinding(
            broker="events",
            physical_topic="tenant.orders",
            direction=EnumBusBindingDirection.PRODUCE,
            consumer_group=group,
        )


@pytest.mark.parametrize(
    ("direction", "group"), [("consume", "readers"), ("produce", None)]
)
def test_duplicate_binding_refused(direction: str, group: str | None) -> None:
    binding = {
        "broker": "events",
        "physical_topic": "tenant.orders",
        "direction": direction,
        "consumer_group": group,
    }
    with pytest.raises(ValidationError, match=r"[Dd]uplicate.*binding"):
        ModelResolvedBusBindings.model_validate(
            {"principal": "reader", "bindings": [binding, dict(binding)]}
        )


def test_distinct_binding_keys_allowed() -> None:
    resolved = ModelResolvedBusBindings.model_validate(
        {
            "principal": "reader",
            "bindings": [
                {
                    "broker": broker,
                    "physical_topic": topic,
                    "direction": direction,
                    "consumer_group": group,
                }
                for broker, topic, direction, group in (
                    ("events", "tenant.orders", "consume", "readers"),
                    ("archive", "tenant.orders", "consume", "readers"),
                    ("events", "tenant.results", "consume", "readers"),
                    ("events", "tenant.orders", "consume", "auditors"),
                    ("events", "tenant.orders", "produce", None),
                )
            ],
        }
    )
    assert len(resolved.bindings) == 5


def test_duplicate_described_group_refused() -> None:
    with pytest.raises(ValidationError, match=r"[Dd]uplicate.*described_groups"):
        ModelResolvedBusBindings(
            principal="reader",
            bindings=(),
            described_groups=(
                ModelBusGroupDescribe(broker="events", group="readers"),
                ModelBusGroupDescribe(broker="events", group="readers"),
            ),
        )


@pytest.mark.parametrize(
    "model",
    [
        ModelBusBinding(
            broker="events",
            physical_topic="tenant.orders",
            direction=EnumBusBindingDirection.PRODUCE,
        ),
        ModelBusGroupDescribe(broker="events", group="readers"),
        ModelResolvedBusBindings(principal="reader", bindings=()),
    ],
)
def test_extra_field_refused(model: BaseModel) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        type(model).model_validate({**model.model_dump(), "unexpected": "value"})


@pytest.mark.parametrize(
    ("model", "field"),
    [
        (
            ModelBusBinding(
                broker="events",
                physical_topic="tenant.orders",
                direction=EnumBusBindingDirection.PRODUCE,
            ),
            "broker",
        ),
        (ModelBusGroupDescribe(broker="events", group="readers"), "group"),
        (ModelResolvedBusBindings(principal="reader", bindings=()), "principal"),
    ],
)
def test_frozen(model: BaseModel, field: str) -> None:
    with pytest.raises(ValidationError, match="frozen_instance"):
        setattr(model, field, "changed")


@pytest.mark.parametrize(
    ("model", "fields"),
    [
        (
            ModelBusBinding(
                broker="events",
                physical_topic="tenant.orders",
                direction=EnumBusBindingDirection.PRODUCE,
            ),
            ("broker", "physical_topic"),
        ),
        (ModelBusGroupDescribe(broker="events", group="readers"), ("broker", "group")),
        (ModelResolvedBusBindings(principal="reader", bindings=()), ("principal",)),
    ],
)
def test_required_strings_nonempty(model: BaseModel, fields: tuple[str, ...]) -> None:
    for field in fields:
        with pytest.raises(ValidationError, match="string_too_short"):
            type(model).model_validate({**model.model_dump(), field: ""})


def test_empty_bindings_allowed() -> None:
    resolved = ModelResolvedBusBindings(principal="reader", bindings=())
    assert resolved.bindings == ()
    assert resolved.described_groups == ()
    assert resolved.brokers() == ()


def test_brokers_sorted_unique() -> None:
    resolved = ModelResolvedBusBindings(
        principal="reader",
        bindings=tuple(
            ModelBusBinding(
                broker=broker,
                physical_topic=topic,
                direction=EnumBusBindingDirection.PRODUCE,
            )
            for broker, topic in (
                ("events", "tenant.orders"),
                ("archive", "tenant.orders"),
                ("events", "tenant.results"),
            )
        ),
        described_groups=(
            ModelBusGroupDescribe(broker="events", group="readers"),
            ModelBusGroupDescribe(broker="archive", group="readers"),
            ModelBusGroupDescribe(broker="events", group="auditors"),
        ),
    )
    assert resolved.brokers() == ("archive", "events")


def test_describe_only_broker_included() -> None:
    resolved = ModelResolvedBusBindings(
        principal="reader",
        bindings=(),
        described_groups=(ModelBusGroupDescribe(broker="archive", group="readers"),),
    )
    assert resolved.brokers() == ("archive",)
