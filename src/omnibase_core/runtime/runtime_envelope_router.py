# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Envelope boundary for the unified runtime dispatch loop (the OMN-14743 fix).

Net-new for the single-runtime / transport-via-DI unification (epic OMN-14717,
ticket OMN-14747; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` sections
(b)/(d.1), HOLE 3). Pure functions, no I/O, no environment reads — isolated here (as
``runtime_fanout_resolver`` isolates routing policy) so the two load-bearing seams are
unit-testable in isolation.

The runtime — NOT the handler — owns the ``ModelEventEnvelope`` boundary (handlers are
def-B: ``handle(request: ModelX) -> ModelY`` and never import the envelope). This module
holds the two halves of that boundary:

* :func:`decode_inbound_envelope` — wire bytes -> ``ModelEventEnvelope`` on the way in.
* :func:`wrap_outbound_envelope` — each emitted fan-out payload -> ``ModelEventEnvelope``
  on the way out, with the correlation chain and a DERIVED, STAMPED ``event_type``.

The durable fix for the delegation drop (OMN-14743 — a silent ``event_type=None`` on
emitted events that a type-scoped consumer then drops): :func:`wrap_outbound_envelope`
derives ``event_type`` from the resolved publish topic (mirroring
``omnibase_infra.runtime.service_dispatch_result_applier._derive_event_type_from_topic``,
OMN-12116) and **FAILS CLOSED** — it raises rather than emit an event whose
``event_type`` would be null. This kills the whole ``event_type``-drop class by
construction: no code path can produce a null-``event_type`` emitted event.

It also bans the ``uuid4`` correlation fallback the infra applier tolerates
(``service_dispatch_result_applier.py:508-512``): a missing inbound ``correlation_id``
raises rather than fabricating a fresh namespace, so the deterministic
``uuid5(correlation_id, "<type>:<idx>")`` envelope ids are byte-reproducible across
redeliveries (plan section (f) golden-chain reproducibility).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid5

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_envelope_metadata import ModelEnvelopeMetadata
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

# The metadata tag key carrying the causation chain (see wrap_outbound_envelope).
CAUSATION_ID_TAG = "causation_id"

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = [
    "CAUSATION_ID_TAG",
    "decode_inbound_envelope",
    "derive_event_type_from_topic",
    "wrap_outbound_envelope",
]


def _default_clock() -> datetime:
    return datetime.now(UTC)


def derive_event_type_from_topic(topic: str) -> str | None:
    """Derive ``{producer}.{event-name}`` from an ONEX topic, else ``None``.

    ONEX topics follow ``onex.{kind}.{producer}.{event-name}.v{n}``; the derived
    ``{producer}.{event-name}`` is the dot-path routing key a type-scoped consumer
    keys on (e.g. ``'omnimarket.swarm-endpoint-health-completed'``). Replicated
    verbatim from the infra applier (``_derive_event_type_from_topic``, OMN-12116);
    core cannot import infra, and the derivation has zero external deps.

    Returns ``None`` for any topic that does not follow the ONEX convention — the
    caller (:func:`wrap_outbound_envelope`) turns that ``None`` into a fail-closed
    raise so a null ``event_type`` can never be emitted.
    """
    parts = topic.split(".")
    if len(parts) >= 5 and parts[0] == "onex":
        producer = parts[2]
        event_name = parts[3]
        return f"{producer}.{event_name}"
    return None


def decode_inbound_envelope(value: bytes) -> ModelEventEnvelope[object]:
    """Decode inbound wire bytes into a ``ModelEventEnvelope`` (the boundary in).

    The runtime's inbound boundary is ``wire bytes -> ModelEventEnvelope`` (plan
    section (b)); the wrapped ``payload`` is left as the raw decoded JSON object (a
    ``dict``) so the ONE coercion (annotation-driven ``model_validate`` against the
    handler's declared def-B input model) can run against it downstream. Fail-closed:
    bytes that are not a valid envelope raise rather than being silently treated as a
    bare payload (the divergence the legacy core adapter had, ``runtime_local_adapter``
    inbound path, which read ``correlation_id`` off a raw payload dict).
    """
    try:
        return ModelEventEnvelope[object].model_validate_json(value)
    except Exception as exc:  # boundary-ok: wire decode failure is surfaced as a typed error, never swallowed
        raise ModelOnexError(
            message=(
                "RuntimeDispatch: failed to decode inbound wire bytes into a "
                "ModelEventEnvelope. The inbound boundary requires an enveloped "
                "message (not a bare payload)."
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc


def wrap_outbound_envelope(
    payload: BaseModel,
    *,
    inbound_envelope: ModelEventEnvelope[object],
    idx: int,
    topic: str,
    clock: Callable[[], datetime] | None = None,
) -> ModelEventEnvelope[BaseModel]:
    """Wrap one emitted fan-out payload in a ``ModelEventEnvelope`` (the boundary out).

    Builds the enveloped-outbound contract (plan I5, HOLE 3) that the runtime — the
    only place with the correlation chain, since def-B handlers never see the envelope
    — must stamp onto every emitted event:

    * ``event_type`` DERIVED from the resolved publish ``topic`` and **FAIL-CLOSED**:
      a null/empty derivation raises (never emit a null-``event_type`` event — the
      OMN-14743 durable fix).
    * ``correlation_id`` propagated from the inbound envelope; a missing inbound
      ``correlation_id`` raises (the ``uuid4`` fallback is banned so the deterministic
      ``uuid5`` id is reproducible — plan section (f)).
    * causality chain: ``metadata.tags[CAUSATION_ID_TAG] = str(inbound.envelope_id)``
      (the immediate parent that caused this emit). It is carried in the metadata tags
      rather than as a first-class ``ModelEventEnvelope`` field on purpose: adding a
      typed ``causation_id`` field to that central wire model would force an
      ``extra="forbid"`` migration (OMN-14515 ratchet) with broad blast radius, out of
      scope for S4. Promoting it to a typed field is the tracked follow-up (plan OPEN
      DECISION 2). The infra applier does not set causation at all today, so this is a
      net add either way.
    * ``envelope_id = uuid5(correlation_id, "<PayloadType>:<idx>")`` — deterministic,
      so redeliveries mint identical ids and downstream can dedupe at-least-once.

    Raises:
        ModelOnexError: if the derived ``event_type`` is null/empty for ``topic``, or
            if the inbound envelope carries no ``correlation_id``.
    """
    event_type = derive_event_type_from_topic(topic)
    if not event_type:
        raise ModelOnexError(
            message=(
                f"RuntimeDispatch: refusing to emit fan-out event {idx} "
                f"({type(payload).__name__}) to topic {topic!r} — the derived "
                "event_type is null/empty. A type-scoped consumer keys on event_type "
                "and would SILENTLY DROP this event (OMN-14743). Emit topics must "
                "follow 'onex.{kind}.{producer}.{event-name}.v{n}'."
            ),
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )

    correlation_id = inbound_envelope.correlation_id
    if correlation_id is None:
        raise ModelOnexError(
            message=(
                f"RuntimeDispatch: refusing to emit fan-out event {idx} "
                f"({type(payload).__name__}) — the inbound envelope carries no "
                "correlation_id, so a deterministic uuid5 envelope_id cannot be minted. "
                "The uuid4 fallback is banned (golden-chain reproducibility, plan "
                "section (f)); the inbound command must carry a correlation_id."
            ),
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )

    resolved_clock = clock or _default_clock
    return ModelEventEnvelope(
        envelope_id=uuid5(correlation_id, f"{type(payload).__name__}:{idx}"),
        payload=payload,
        correlation_id=correlation_id,
        metadata=ModelEnvelopeMetadata(
            tags={CAUSATION_ID_TAG: str(inbound_envelope.envelope_id)}
        ),
        event_type=event_type,
        payload_type=type(payload).__name__,
        envelope_timestamp=resolved_clock(),
    )
