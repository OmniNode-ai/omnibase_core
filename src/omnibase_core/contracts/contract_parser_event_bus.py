# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event Bus Contract Parser.

Parses the ``event_bus`` block of a node contract into a normalized list of
subscriptions. Supports two shapes:

1. **Classic** (``event_bus.subscribe_topics``): ``list[str]`` of topic suffixes.
2. **Nested** (``event_bus.subscribe``): ``list[dict]`` with required ``topic``
   and optional ``consumer_group``.

Both shapes may coexist in a single contract; classic entries are emitted first.
Unknown shapes (or a recognized shape missing required fields) raise
:class:`EventBusContractShapeError` so silent subscription drops cannot occur.
"""

from __future__ import annotations

from omnibase_core.errors.error_event_bus_contract_shape import (
    EventBusContractShapeError,
)
from omnibase_core.models.contracts.model_event_bus_parse_result import (
    ModelEventBusParseResult,
)
from omnibase_core.models.contracts.model_event_bus_subscription import (
    ModelEventBusSubscription,
)

_RECOGNIZED_KEYS: frozenset[str] = frozenset({"subscribe_topics", "subscribe"})


def parse_event_bus(contract: dict[str, object]) -> ModelEventBusParseResult:
    """Parse the ``event_bus`` block of a contract into normalized subscriptions.

    Args:
        contract: A loaded node contract (typically from YAML). Missing
            ``event_bus`` is treated as zero subscriptions.

    Returns:
        A :class:`ModelEventBusParseResult` containing every subscription
        declared by either the classic or nested shape.

    Raises:
        EventBusContractShapeError: ``event_bus`` is not a mapping, contains a
            recognized shape with malformed entries, or contains only
            unrecognized keys.
    """
    event_bus = contract.get("event_bus")
    if event_bus is None:
        return ModelEventBusParseResult()

    if not isinstance(event_bus, dict):
        raise EventBusContractShapeError(
            f"event_bus must be a mapping, got {type(event_bus).__name__}",
        )

    unknown = sorted(set(event_bus.keys()) - _RECOGNIZED_KEYS)
    if unknown:
        raise EventBusContractShapeError(
            "event_bus contains unrecognized keys; "
            f"got keys {unknown!r}, expected only 'subscribe_topics' or 'subscribe'",
        )

    subscriptions: list[ModelEventBusSubscription] = []

    if "subscribe_topics" in event_bus:
        classic = event_bus["subscribe_topics"]
        if not isinstance(classic, list):
            raise EventBusContractShapeError(
                "event_bus.subscribe_topics must be a list of topic strings",
            )
        for topic in classic:
            if not isinstance(topic, str):
                raise EventBusContractShapeError(
                    "event_bus.subscribe_topics entries must be strings",
                )
            subscriptions.append(ModelEventBusSubscription(topic=topic))

    if "subscribe" in event_bus:
        nested = event_bus["subscribe"]
        if not isinstance(nested, list):
            raise EventBusContractShapeError(
                "event_bus.subscribe must be a list of subscription mappings",
            )
        for entry in nested:
            if not isinstance(entry, dict):
                raise EventBusContractShapeError(
                    "event_bus.subscribe entries must be mappings",
                )
            topic = entry.get("topic")
            if not isinstance(topic, str):
                raise EventBusContractShapeError(
                    "event_bus.subscribe entries require a 'topic' string field",
                )
            consumer_group = entry.get("consumer_group")
            if consumer_group is not None and not isinstance(consumer_group, str):
                raise EventBusContractShapeError(
                    "event_bus.subscribe[*].consumer_group must be a string when present",
                )
            subscriptions.append(
                ModelEventBusSubscription(
                    topic=topic,
                    consumer_group=consumer_group,
                ),
            )

    return ModelEventBusParseResult(subscriptions=subscriptions)


__all__ = ["parse_event_bus"]
