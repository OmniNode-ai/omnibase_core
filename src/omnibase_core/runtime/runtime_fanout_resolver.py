# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shared pure fan-out publish-topic resolver (OMN-14403 §6ii, def-B multi-event).

THE single source of truth for how a def-B handler's returned event model(s) are
mapped to publish topics. Consumed by BOTH runtimes:

* ``LocalRuntimeBusAdapter`` (``omnibase_core.runtime.runtime_local_adapter``) — the
  ``onex node`` / in-memory path; and
* the Kafka auto-wiring (``omnibase_infra.runtime.auto_wiring.fanout_seam`` +
  ``handler_wiring._normalize_handler_result``) — the live kernel path.

Why one shared module and not a copy on each side: two copies is exactly how the
runtimes drifted before. The Kafka ``_normalize_handler_result`` grew a fan-out
branch while ``LocalRuntimeBusAdapter`` had none, so ``onex run-node`` and the
live kernel disagreed byte-for-byte on what a def-B fan-out handler publishes
(memory ``reference_runtime_local_vs_kafka_adapter_divergence``; Fable refinement
3, ``docs/plans/2026-07-14-p3a-sanctioned-direction-design.md`` §6). This module
is the one resolver both call so they cannot diverge again.

Resolution rules (all fail-closed — a def-B fan-out return that cannot be routed
must RAISE, never silently fall back to a single ``output_topic`` and misroute):

1. **Exact type, no subclass walk.** A returned element's topic is resolved from
   ``type(element).__name__`` (short name — ``Model`` prefix stripped — then the
   full class name), matching the applier's ``_resolve_mapped_output_topic``. A
   subclass walk is deliberately NOT done: it would hide a silent misroute.
2. **Fail-closed on unmapped.** A class absent from ``published_events`` raises.
3. **Reject carriers.** ``ModelEventEnvelope`` / ``ModelDelegationEventEnvelope``
   and any element that carries a non-empty embedded ``topic`` field are rejected:
   fan-out elements are pure domain payloads; the topic stays contract-declared.
4. **Injectivity asserted at boot.** ``published_events`` must be an injective
   class -> topic map (one class -> exactly one topic; one topic carries exactly
   one wire model). Ambiguity fails at wiring time, not at event k.

This module performs NO I/O and reads NO environment. The seam's on/off decision
and the ``published_events`` load are the caller's responsibility.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = [
    "CARRIER_CLASS_NAMES",
    "assert_published_events_injective",
    "is_fanout_sequence",
    "normalize_fanout_elements",
    "resolve_fanout_topics",
    "resolve_published_topic",
]

# Routing carriers a fan-out sequence must never contain. A carrier smuggled into
# a fan-out return would hijack routing via its embedded ``event_type`` ahead of
# the contract's published_events (the OMN-13247 precedence), defeating the
# contract-declared topic. Mirrors ``fanout_seam._FANOUT_CARRIER_CLASSES``.
CARRIER_CLASS_NAMES: frozenset[str] = frozenset(
    {"ModelEventEnvelope", "ModelDelegationEventEnvelope"}
)


def is_fanout_sequence(result: object) -> bool:
    """Return True when a handler return is the def-B fan-out shape.

    A ``Sequence`` return that is not a scalar ``str``/``bytes`` and not a single
    ``BaseModel`` (which takes its own single-emit branch) is a fan-out batch.
    """
    return isinstance(result, Sequence) and not isinstance(
        result, str | bytes | BaseModel
    )


def _short_name(class_name: str) -> str:
    """Return the applier's short spelling of a class name (``Model`` stripped)."""
    return class_name.removeprefix("Model")


def _reject_carrier(element: BaseModel, idx: int, message_type: str | None) -> None:
    """Raise if a fan-out element is a routing carrier or names its own topic."""
    class_name = type(element).__name__
    if class_name in CARRIER_CLASS_NAMES:
        raise ModelOnexError(
            message=(
                f"Fan-out element {idx} is a routing carrier ({class_name}), not a "
                "domain payload. A def-B fan-out handler returns pure typed event "
                "models; the topic is resolved from each element's class via the "
                f"contract's published_events. (handler message_type={message_type!r})"
            ),
            error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
        )
    embedded_topic = getattr(element, "topic", None)
    if isinstance(embedded_topic, str) and embedded_topic.strip():
        raise ModelOnexError(
            message=(
                f"Fan-out element {idx} ({class_name}) carries an embedded topic "
                f"{embedded_topic.strip()!r}, which would override the contract's "
                "published_events routing. Topics stay contract-declared — remove "
                f"the topic field from the emitted model. (handler "
                f"message_type={message_type!r})"
            ),
            error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
        )


def normalize_fanout_elements(
    elements: Sequence[object],
    *,
    message_type: str | None = None,
) -> list[BaseModel]:
    """Validate a fan-out sequence into a list of routable payloads — never filter.

    Validate-then-RAISE: a filter (``[e for e in seq if isinstance(e, BaseModel)]``)
    would silently drop a non-model element and pass the rest as success — the same
    silent-drop disease the seam exists to kill, one level down. Order is preserved.
    """
    validated: list[BaseModel] = []
    for idx, element in enumerate(elements):
        if not isinstance(element, BaseModel):
            raise ModelOnexError(
                message=(
                    f"Fan-out element {idx} is {type(element).__name__}, not a "
                    "BaseModel. A def-B fan-out handler returns an ordered sequence "
                    "of typed event models; a non-model element cannot be routed to "
                    f"a topic. (handler message_type={message_type!r})"
                ),
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            )
        _reject_carrier(element, idx, message_type)
        validated.append(element)
    return validated


def resolve_published_topic(
    published_events: Mapping[str, str],
    element: BaseModel,
    *,
    message_type: str | None = None,
) -> str:
    """Resolve one fan-out element's publish topic from ``published_events``.

    Exact-type lookup (short name then full class name), matching the applier's
    ``_resolve_mapped_output_topic``. Fail-closed: an unmapped class raises rather
    than falling back to a single ``output_topic`` and silently misrouting.
    """
    class_name = type(element).__name__
    topic = published_events.get(_short_name(class_name))
    if topic is None:
        topic = published_events.get(class_name)
    if topic is None:
        raise ModelOnexError(
            message=(
                f"Fan-out element {class_name!r} is not declared in the contract's "
                f"published_events {sorted(published_events)}. A def-B fan-out "
                "handler's emitted classes must all be contract-declared — there is "
                "no silent fallback to a single output_topic (that would misroute). "
                f"(handler message_type={message_type!r})"
            ),
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )
    return topic


def resolve_fanout_topics(
    published_events: Mapping[str, str],
    elements: Sequence[object],
    *,
    message_type: str | None = None,
) -> list[tuple[str, BaseModel]]:
    """Resolve a fan-out sequence into ordered ``(topic, payload)`` pairs.

    Validates the elements (carrier rejection, model-only), then resolves each
    element's topic. Order is the handler's return order — the load-bearing
    property the routing-equivalence proof asserts.
    """
    validated = normalize_fanout_elements(elements, message_type=message_type)
    return [
        (
            resolve_published_topic(
                published_events, element, message_type=message_type
            ),
            element,
        )
        for element in validated
    ]


def assert_published_events_injective(
    published_events: Mapping[str, str],
    *,
    context: str,
) -> None:
    """Assert ``published_events`` is an injective class -> topic map (boot check).

    Two invariants, both a wiring-time (not event-k) failure:

    * **Well-defined:** a single class must not map to two topics. The map is keyed
      by class name in either spelling (``Foo`` and ``ModelFoo``); those collapse to
      one canonical class, and if they name different topics the map is ambiguous.
    * **Injective:** two distinct classes must not map to the same topic. One topic
      carries exactly one wire model on the bus; if a model must reach two topics,
      mint two types (Fable refinement 3).

    ``context`` names the contract/handler for the error message. A silently
    non-injective map is how an unmapped element would misroute, so this refuses
    at boot rather than degrade at publish time.
    """
    canonical_to_topic: dict[str, str] = {}
    for key, topic in published_events.items():
        canonical = _short_name(key)
        prior = canonical_to_topic.get(canonical)
        if prior is not None and prior != topic:
            raise ModelOnexError(
                message=(
                    f"published_events for {context} maps class {canonical!r} to two "
                    f"topics ({prior!r} and {topic!r}). A class must resolve to exactly "
                    "one topic; reconcile the duplicate entry."
                ),
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            )
        canonical_to_topic[canonical] = topic

    classes_by_topic: dict[str, set[str]] = defaultdict(set)
    for canonical, topic in canonical_to_topic.items():
        classes_by_topic[topic].add(canonical)
    for topic, classes in classes_by_topic.items():
        if len(classes) > 1:
            raise ModelOnexError(
                message=(
                    f"published_events for {context} maps {sorted(classes)} all to "
                    f"topic {topic!r}. The fan-out resolver requires an injective "
                    "class -> topic map (one topic carries exactly one wire model); "
                    "mint distinct topics or a single distinct type."
                ),
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            )
