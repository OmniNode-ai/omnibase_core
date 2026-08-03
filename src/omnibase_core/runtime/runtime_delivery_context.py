# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The adapter surface that populates ``ModelDeliveryContext`` at the receipt
boundary (OMN-15665).

Pure function, no I/O — isolated here the same way ``runtime_envelope_router``
isolates the envelope boundary, so this load-bearing seam is unit-testable in
isolation and reusable unchanged against any transport.

``topic`` / ``partition`` / ``offset`` are the broker-assigned coordinates the
transport already carries on the polled record — copied verbatim, never
re-derived. ``envelope_id`` is the one field that needs care: it is read directly
from the RAW wire bytes (a fresh ``json.loads``, independent of
``ModelEventEnvelope`` parsing) rather than from the pydantic-validated envelope.
``ModelEventEnvelope.envelope_id`` is declared with ``default_factory=uuid4``, so
a record whose wire bytes never truthfully carried an ``envelope_id`` would
otherwise silently validate into a **freshly fabricated** id — exactly the
fabrication class ("never a ``uuid4()``-fabricated fallback") this ticket exists
to close. Re-parsing the raw bytes here is the only way to tell "the wire
genuinely carried this id" apart from "pydantic quietly minted one".

This module intentionally imports no ``omnibase_core.protocols`` symbol (only
``json``, ``uuid.UUID``, the error model, and ``ModelDeliveryContext`` — a plain
model import, not a protocols-hub edge) so it adds no new importer to the frozen
``protocols`` hub (OMN-14340 growth ratchet).
"""

from __future__ import annotations

import json
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.model_delivery_context import ModelDeliveryContext

__all__ = ["build_delivery_context"]


def build_delivery_context(
    *, topic: str, partition: int, offset: int, raw_value: bytes
) -> ModelDeliveryContext:
    """Build the immutable, broker-populated-only delivery context for one record.

    Fails closed (``ModelOnexError``) rather than fabricate an identity when:
    * ``raw_value`` is not valid JSON, or not a JSON object;
    * the ``envelope_id`` key is absent or ``null``;
    * ``envelope_id`` is not a parsable UUID;
    * ``partition`` / ``offset`` is negative (a fabricated sentinel, never a
      legitimate broker-assigned coordinate).

    ``topic`` / ``partition`` / ``offset`` are the caller's own broker
    coordinates (the polled transport message), passed through verbatim.
    """
    try:
        raw = json.loads(raw_value)
    except Exception as exc:  # boundary-ok: malformed wire bytes are surfaced as a typed error, never treated as a bare/empty envelope
        raise ModelOnexError(
            message=(
                "build_delivery_context: raw wire bytes are not valid JSON — "
                "cannot recover an authoritative envelope_id."
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc

    if not isinstance(raw, dict):
        raise ModelOnexError(
            message=(
                "build_delivery_context: decoded wire JSON is not an object — "
                f"got {type(raw).__name__}; cannot recover an authoritative "
                "envelope_id."
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    raw_envelope_id = raw.get("envelope_id")
    if raw_envelope_id is None:
        raise ModelOnexError(
            message=(
                "build_delivery_context: wire record carries no envelope_id — "
                "refusing to fabricate one (never uuid4()-fallback at the "
                "receipt boundary)."
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    try:
        envelope_id = UUID(str(raw_envelope_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ModelOnexError(
            message=(
                "build_delivery_context: wire envelope_id "
                f"{raw_envelope_id!r} is not a parsable UUID."
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc

    try:
        return ModelDeliveryContext(
            envelope_id=envelope_id,
            topic=topic,
            partition=partition,
            offset=offset,
        )
    except Exception as exc:  # boundary-ok: pydantic validation (e.g. negative coordinate) is surfaced as a typed error at this boundary
        raise ModelOnexError(
            message=(
                "build_delivery_context: refusing to build a delivery context "
                f"for topic={topic!r} partition={partition} offset={offset} — "
                f"{exc}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
