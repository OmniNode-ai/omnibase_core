# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Single authoritative transport-envelope unwrap predicate (OMN-12960).

The runtime wraps a domain payload in a transport envelope before it reaches a
handler. Two distinct outer shapes reach the coercion / dispatch boundary and
BOTH must be recognised:

1. The dispatch-engine *materialized* shape — the only shape the live runtime
   actually delivers to ``handle()`` for contracts whose ``handler_routing``
   declares no ``event_model`` (auto-wiring passes the materialized dict raw).
   Outer keys are exactly ``{"payload", "__bindings", "__debug_trace"}`` — the
   real ``partition_key`` lives *inside* ``__debug_trace``, not at the top
   level. See
   ``omnibase_infra.runtime.message_dispatch_engine._materialize_envelope_with_bindings``.
2. The bare envelope-field shape (``partition_key`` / ``event_type`` /
   ``correlation_id`` at the top level) — non-materialized deliveries.

Domain models never declare these transport keys, so splatting the raw envelope
into ``Model(**payload)`` raises a ``ValidationError`` with every required field
reported missing. Unwrapping recursively at the boundary keeps the domain models
transport-agnostic.

History and rationale
---------------------
This predicate previously existed as **two** hand-maintained marker-key sets —
``omnibase_infra.runtime.auto_wiring.handler_wiring._ENVELOPE_MARKER_KEYS`` and
``omnimarket.nodes.evidence_pipeline_native._ENVELOPE_MARKER_KEYS``. Each was
"fixed" once already (OMN-12940 added the infra recursion; OMN-12946 added
``__debug_trace`` / ``__bindings`` to the omnimarket set), and they drifted
again: as of OMN-12960 the infra set was missing ``__bindings`` while the
omnimarket set carried it. A materialized envelope whose only marker is
``__bindings`` would therefore unwrap on the omnimarket side and silently fail
to unwrap on the infra side. A hand-synced cross-repo constant cannot be made
safe; the single source of truth lives here and both call sites import it.

Layering note (OMN-12960)
-------------------------
By layering this wire-level concern belongs in ``omnibase_compat`` (lowest,
zero upstream runtime deps). The compat pin is policy-frozen — bumping it is a
symptom of models that should have graduated, not a fix — so per the P1.4 plan
the predicate is sited in ``omnibase_core`` (already a runtime dependency of
both ``omnibase_infra`` and ``omnimarket``) instead. When the compat pin
un-freezes, this module moves to compat verbatim and the imports follow.
"""

from __future__ import annotations

# dispatch-surface-test-ok: omnibase_core hosts no live dispatcher; this is the
# pure unwrap predicate. Its real-dispatch-path coverage lives in omnibase_infra
# (handler_wiring) and omnimarket (evidence_pipeline_native), where the predicate
# is wired into the dispatcher and the mandatory real-dispatch fixture exercises it.
from collections.abc import Mapping
from typing import cast

__all__ = [
    "ENVELOPE_MARKER_KEYS",
    "is_transport_envelope",
    "unwrap_transport_envelope",
]

# Transport-envelope keys that the runtime adds around the domain payload.
# A mapping that carries a ``payload`` mapping plus at least one of these keys
# is a transport envelope, not a domain model that merely declares its own
# ``payload`` field. ``__bindings`` and ``__debug_trace`` are the
# dispatch-engine *materialized* markers and MUST stay in this set — dropping
# either silently turns the unwrap back into a no-op on live dispatch (the
# OMN-12946 / OMN-12960 defect class).
ENVELOPE_MARKER_KEYS: frozenset[str] = frozenset(
    {
        "partition_key",
        "event_type",
        "envelope_id",
        "event_id",
        "correlation_id",
        "__debug_trace",
        "__bindings",
    }
)


def is_transport_envelope(value: object) -> bool:
    """Return True when ``value`` is a transport envelope wrapping a payload.

    A transport envelope is a mapping that carries a ``payload`` mapping plus at
    least one transport marker key. Requiring a marker avoids over-unwrapping a
    legitimate domain model that happens to declare its own ``payload`` field.
    """
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("payload"), Mapping)
        and bool(ENVELOPE_MARKER_KEYS & value.keys())
    )


def unwrap_transport_envelope[T](payload: T) -> T | Mapping[str, object]:
    """Return the domain payload, unwrapping any transport envelope around it.

    Handles three delivery shapes, recursively, until the domain payload is
    reached:

    * an object exposing a populated ``.payload`` attribute
      (a ``ModelEventEnvelope`` instance);
    * a materialized dispatch dict
      (``{"payload": {...}, "__bindings": ..., "__debug_trace": ...}``);
    * a bare-marker envelope dict
      (``{"payload": {...}, "partition_key": ...}``).

    A mapping that carries a ``payload`` field but **no** transport marker is
    returned unchanged — it is treated as a domain model that legitimately owns
    a ``payload`` field, never as an envelope.
    """
    # Object form: ModelEventEnvelope (or any object exposing a populated
    # ``payload`` attribute). Mappings are handled by the marker check below.
    if not isinstance(payload, Mapping):
        nested = getattr(payload, "payload", None)
        if nested is not None:
            return unwrap_transport_envelope(nested)
        return payload
    # Mapping form: only unwrap when it is a transport envelope (carries a
    # ``payload`` mapping plus a marker), never when ``payload`` is a domain
    # field on the model itself.
    if is_transport_envelope(payload):
        inner = cast("Mapping[str, object]", payload["payload"])
        return unwrap_transport_envelope(inner)
    return payload
