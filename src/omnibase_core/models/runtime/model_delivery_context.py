# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical immutable delivery context (OMN-15665).

The truthful, RuntimeDispatch-context-resident identity of one inbound record:
the broker-assigned coordinates (``topic`` / ``partition`` / ``offset``) plus the
envelope's own authoritative ``envelope_id`` — as delivered, never re-derived,
never a ``uuid4()`` fallback.

This is Core-resident by the same layering logic as
``docs/architecture/layering-exceptions.yaml`` LAYER-EXC-001/002: it is the
canonical identity RuntimeDispatch depends on for the receipt boundary, and
RuntimeDispatch is Core-resident. It is deliberately **separate** from the def-B
handler argument (``handle(request: ModelX) -> ModelY``) — no handler signature
ever gains a second parameter for this. Adding one hard-fails the OMN-14355
canon-shape ratchet.

Authority: the 2026-08-02 lab-readiness ruling (accepted refinement 4, "Canonical
delivery context stays outside def-B") and Linear comment ``cfb64e0f`` on
OMN-15666 (the frozen r2 contract decision, which reproduces this exact
four-field shape as the reference the R2 golden-RED harness validates against —
``omninode_infra``'s
``tests/fixtures/omn_15663_r2/target_models.py::ModelDeliveryContext``).

``partition`` and ``offset`` reject negative values: a ``-1`` (or any negative)
coordinate is a fabricated sentinel, never a legitimate broker-assigned position.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

_NONNEGATIVE_MSG = (
    "must be a nonnegative broker-assigned coordinate, not a fabricated sentinel"
)


class ModelDeliveryContext(BaseModel):
    """Immutable, broker-populated-only delivery identity for one inbound record.

    Frozen value object; `extra="forbid"` — exactly the four fields below, no more.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    envelope_id: UUID
    """The inbound envelope's own authoritative id, as delivered on the wire.

    Never a fresh ``uuid4()``, never aliased from ``correlation_id`` — an absent or
    unparsable wire ``envelope_id`` fails closed at the receipt boundary (see
    ``omnibase_core.runtime.runtime_delivery_context.build_delivery_context``)."""

    topic: str
    """Source topic the record was polled from (broker coordinate, verbatim)."""

    partition: int
    """Partition the record belongs to (broker coordinate, verbatim)."""

    offset: int
    """Monotonic per-partition offset of the record (broker coordinate, verbatim)."""

    @field_validator("partition", "offset")
    @classmethod
    def _nonnegative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(_NONNEGATIVE_MSG)
        return value


__all__ = ["ModelDeliveryContext"]
