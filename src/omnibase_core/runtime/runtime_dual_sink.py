# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dual-sink terminal durability: primary DLQ, then canonical quarantine (OMN-15666).

The reusable runtime primitive this ticket owns. Pure ordering + commit
invariant over an injected acknowledging ``publish`` callable; no I/O of its
own, no transport import, no Kafka knowledge — so the SAME scenario table
exercises it against a mock sink, a real Kafka producer, and a real durable
persistence dependency without editing a single assertion.

The invariant, in one place
---------------------------
1. Attempt the primary DLQ **exactly once**.
2. On acknowledgement: return a ``ModelPrimaryDlqDispositionReceipt`` carrying
   the BROKER-returned coordinates. Quarantine is never called.
3. On failure: capture typed ``ModelDeliveryFailureEvidence`` for it and attempt
   the canonical quarantine sink once, publishing OMN-15667's
   ``ModelQuarantineWirePayload`` (which carries that primary failure).
4. On quarantine acknowledgement: return a
   ``ModelQuarantineDispositionReceipt``.
5. On BOTH failing: raise :class:`DualPublishFailureError` naming both failures.
   The caller MUST NOT commit the source offset — restart/replay reprocesses the
   same source record.

A receipt is returned only against a broker acknowledgement. An enqueue intent,
a successful serialization, a swallowed exception, or an un-awaited publish
future never produces one — the acknowledgement is the gate (OMN-15666
acceptance criterion 6).

Injected bindings and their canonical protocols
-----------------------------------------------
The two injected dependencies (an acknowledging publish callable and a durable,
identity-keyed disposition store) have canonical public protocols at
``omnibase_core.protocols.runtime.protocol_acknowledging_publish`` and
``...protocol_terminal_disposition_store`` — both generic and model-free, so
they add no ``protocols -> models`` edge (frozen at 65).

This module deliberately does NOT import them. It declares private STRUCTURAL
MIRRORS below instead, the same pattern (and for the same reason) as
``runtime_dispatch.py``'s transport mirrors: importing a ``protocols`` symbol
from a net-new ``runtime`` module adds a new importer to the frozen
``protocols`` hub, which HARD-FAILs the OMN-14340 growth ratchet
(``scripts/ci/check_import_ratchet.py``). Each mirror is a strict SUBSET of its
canonical protocol, so any object satisfying the canonical protocol satisfies
the mirror — and ``tests/unit/runtime/test_runtime_dual_sink_durability.py``
binds the concrete test implementations to the CANONICAL protocol types, so the
suite fails if a mirror ever drifts from its source of truth.

``DualPublishFailureError`` lives in the sibling ``runtime_dual_sink_failure``
module (ONEX single-class-per-file) and is re-exported here because this module
is the only thing that raises it.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from typing import Protocol

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)
from omnibase_core.models.event_bus.model_primary_dlq_wire_payload import (
    ModelPrimaryDlqWirePayload,
)
from omnibase_core.models.event_bus.model_quarantine_wire_payload import (
    ModelQuarantineWirePayload,
)
from omnibase_core.models.event_bus.model_transport_publish_acknowledgement import (
    ModelTransportPublishAcknowledgement,
)
from omnibase_core.models.runtime.model_delivery_context import ModelDeliveryContext
from omnibase_core.models.runtime.model_primary_dlq_disposition_receipt import (
    ModelPrimaryDlqDispositionReceipt,
)
from omnibase_core.models.runtime.model_quarantine_disposition_receipt import (
    ModelQuarantineDispositionReceipt,
)
from omnibase_core.models.runtime.model_terminal_disposition_request import (
    ModelTerminalDispositionRequest,
)
from omnibase_core.runtime.runtime_dual_sink_failure import DualPublishFailureError

__all__ = [
    "PRIMARY_DLQ_PUBLISH_STAGE",
    "QUARANTINE_PUBLISH_STAGE",
    "DualPublishFailureError",
    "ModelTerminalDispositionReceipt",
    "build_primary_dlq_wire_payload",
    "build_quarantine_wire_payload",
    "build_terminal_disposition_request",
    "execute_terminal_disposition_once",
    "resolve_terminal_disposition",
]

PRIMARY_DLQ_PUBLISH_STAGE = "primary_dlq_publish"
"""``ModelDeliveryFailureEvidence.stage`` for a failed primary-DLQ publish."""

QUARANTINE_PUBLISH_STAGE = "quarantine_publish"
"""``ModelDeliveryFailureEvidence.stage`` for a failed quarantine publish."""

ModelTerminalDispositionReceipt = (
    ModelPrimaryDlqDispositionReceipt | ModelQuarantineDispositionReceipt
)
"""The two — and only two — durable terminal outcomes of the dual-sink path."""

# Deterministic failure classes: retrying the identical bytes reproduces them
# byte-for-byte, so ``retryable`` is False. Anything else (transport, timeout,
# broker unavailability) is classified retryable — fail-OPEN on retryability is
# safe here because retryability is descriptive evidence for the quarantine
# consumer, never a gate this module itself branches on.
_NON_RETRYABLE_FAILURES: tuple[type[BaseException], ...] = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


# --- private structural mirrors of the canonical protocols (see docstring) ---


class _AcknowledgingPublishLike(Protocol):
    """Subset mirror of ``ProtocolAcknowledgingPublish[ModelTransportPublishAcknowledgement]``."""

    async def __call__(
        self,
        *,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Sequence[tuple[str, bytes]],
    ) -> ModelTransportPublishAcknowledgement: ...


class _TerminalDispositionStoreLike(Protocol):
    """Subset mirror of ``ProtocolTerminalDispositionStore[ModelDeliveryContext, ModelTerminalDispositionReceipt]``."""

    async def load(
        self, context: ModelDeliveryContext
    ) -> ModelTerminalDispositionReceipt | None: ...

    async def save(
        self, context: ModelDeliveryContext, receipt: ModelTerminalDispositionReceipt
    ) -> None: ...


def _classify_retryable(exc: BaseException) -> bool:
    """Descriptive retryability for the quarantine consumer (never a local gate)."""
    return not isinstance(exc, _NON_RETRYABLE_FAILURES)


def _evidence(
    *, stage: str, exc: BaseException, topic: str
) -> ModelDeliveryFailureEvidence:
    return ModelDeliveryFailureEvidence(
        stage=stage,
        error_type=type(exc).__name__,
        error_message=f"publish to {topic!r} failed: {exc}",
        retryable=_classify_retryable(exc),
    )


def _encode_headers(
    headers: Sequence[tuple[str, bytes]] | Mapping[str, bytes],
) -> tuple[tuple[str, str], ...]:
    """Base64 header VALUES, preserving order and duplicate names.

    A ``Mapping`` input has ALREADY lost duplicates before reaching here (a
    limitation inherited from the frozen ``ProtocolTransportMessage.headers``
    surface, which is a ``Mapping[str, bytes]``); its iteration order is
    preserved verbatim. Pass a ``Sequence`` wherever the transport exposes one
    to keep duplicates.
    """
    pairs: Sequence[tuple[str, bytes]] = (
        tuple(headers.items()) if isinstance(headers, Mapping) else tuple(headers)
    )
    return tuple(
        (name, base64.b64encode(value).decode("ascii")) for name, value in pairs
    )


def _decode_headers(
    headers_b64: Sequence[tuple[str, str]],
) -> tuple[tuple[str, bytes], ...]:
    return tuple((name, base64.b64decode(value)) for name, value in headers_b64)


def build_terminal_disposition_request(
    *,
    context: ModelDeliveryContext,
    primary_dlq_topic: str,
    quarantine_topic: str,
    source_key: bytes | None,
    source_value: bytes,
    source_headers: Sequence[tuple[str, bytes]] | Mapping[str, bytes],
    source_failure: ModelDeliveryFailureEvidence,
) -> ModelTerminalDispositionRequest:
    """Project a ``ModelDeliveryContext`` + the raw record into a disposition input.

    The four ``source_*`` identity fields are copied VERBATIM from ``context``.
    No ``correlation_id`` alias, no ``uuid4()`` substitution, no re-derivation —
    the context is already the fail-closed authoritative identity built at the
    receipt boundary by ``build_delivery_context`` (OMN-15665).
    """
    return ModelTerminalDispositionRequest(
        source_envelope_id=context.envelope_id,
        source_topic=context.topic,
        source_partition=context.partition,
        source_offset=context.offset,
        primary_dlq_topic=primary_dlq_topic,
        quarantine_topic=quarantine_topic,
        # DOCUMENTED COLLAPSE (CodeRabbit, minor): a present-but-empty key
        # (b"") and an absent key (None) both encode to "". The merged
        # OMN-15667 ``ModelQuarantineWirePayload.source_key_b64`` is a
        # REQUIRED ``str``, so widening this to ``str | None`` here would
        # break field-by-field seam parity with an accepted parent model.
        # Consequence is placement-only, never identity: the DLQ/quarantine
        # copy of an empty-key source record is published with key=None and
        # so loses deterministic partition placement. Dedupe is unaffected —
        # it keys on the four-field source tuple carried IN the payload, not
        # on the Kafka key.
        source_key_b64=base64.b64encode(source_key or b"").decode("ascii"),
        source_value_b64=base64.b64encode(source_value).decode("ascii"),
        source_headers_b64=_encode_headers(source_headers),
        source_failure=source_failure,
    )


def build_primary_dlq_wire_payload(
    request: ModelTerminalDispositionRequest,
) -> ModelPrimaryDlqWirePayload:
    """Pre-ack primary-DLQ payload — a pure projection of ``request``."""
    return ModelPrimaryDlqWirePayload(
        source_envelope_id=request.source_envelope_id,
        source_topic=request.source_topic,
        source_partition=request.source_partition,
        source_offset=request.source_offset,
        source_key_b64=request.source_key_b64,
        source_value_b64=request.source_value_b64,
        source_headers_b64=request.source_headers_b64,
        source_failure=request.source_failure,
    )


def build_quarantine_wire_payload(
    request: ModelTerminalDispositionRequest,
    primary_failure: ModelDeliveryFailureEvidence,
) -> ModelQuarantineWirePayload:
    """Pre-ack quarantine payload (OMN-15667 shape) carrying the primary failure.

    ``source_failure`` is the PRIMARY-DLQ publish failure, matching the accepted
    OMN-15667 semantics: by the time a record reaches quarantine, the failure
    that put it there is the failed primary-DLQ publish. The original handling
    failure remains addressable through the source bytes.
    """
    return ModelQuarantineWirePayload(
        source_envelope_id=request.source_envelope_id,
        source_topic=request.source_topic,
        source_partition=request.source_partition,
        source_offset=request.source_offset,
        source_key_b64=request.source_key_b64,
        source_value_b64=request.source_value_b64,
        source_headers_b64=request.source_headers_b64,
        primary_dlq_error_type=primary_failure.error_type,
        primary_dlq_error_message=primary_failure.error_message,
        source_failure=primary_failure,
    )


async def resolve_terminal_disposition(
    *,
    request: ModelTerminalDispositionRequest,
    publish: _AcknowledgingPublishLike,
) -> ModelTerminalDispositionReceipt:
    """Primary DLQ once, then quarantine; raise if neither becomes durable.

    Returns the receipt built from the BROKER's acknowledgement (never from the
    intended topic on ``request``). Raises :class:`DualPublishFailureError` when
    both sinks fail — the caller must leave the source offset uncommitted.
    """
    primary_payload = build_primary_dlq_wire_payload(request)
    source_headers = _decode_headers(request.source_headers_b64)
    source_key = base64.b64decode(request.source_key_b64) or None

    try:
        ack = await publish(
            topic=request.primary_dlq_topic,
            key=source_key,
            value=primary_payload.model_dump_json().encode("utf-8"),
            headers=source_headers,
        )
    except Exception as exc:  # noqa: BLE001 — boundary-ok: ANY primary-sink failure must reach quarantine, so the catch is deliberately total. It is not a swallow: the exception is CAPTURED as typed ModelDeliveryFailureEvidence, embedded in the quarantine payload, and re-surfaced on DualPublishFailureError. Narrowing it would let an unanticipated transport error escape as an uncaught raise, skipping the fallback sink entirely — the exact durability hole this ticket closes.
        primary_failure = _evidence(
            stage=PRIMARY_DLQ_PUBLISH_STAGE,
            exc=exc,
            topic=request.primary_dlq_topic,
        )
    else:
        return ModelPrimaryDlqDispositionReceipt(
            primary_dlq_payload=primary_payload,
            primary_dlq_topic=ack.topic,
            primary_dlq_partition=ack.partition,
            primary_dlq_offset=ack.offset,
        )

    quarantine_payload = build_quarantine_wire_payload(request, primary_failure)
    try:
        ack = await publish(
            topic=request.quarantine_topic,
            key=source_key,
            value=quarantine_payload.model_dump_json().encode("utf-8"),
            headers=source_headers,
        )
    except Exception as exc:  # boundary-ok: the DUAL failure is SURFACED as a typed error the caller converts into "do not commit" — the whole point of this primitive.
        raise DualPublishFailureError(
            primary_failure=primary_failure,
            quarantine_failure=_evidence(
                stage=QUARANTINE_PUBLISH_STAGE,
                exc=exc,
                topic=request.quarantine_topic,
            ),
            source_envelope_id=request.source_envelope_id,
            source_topic=request.source_topic,
            source_partition=request.source_partition,
            source_offset=request.source_offset,
        ) from exc

    return ModelQuarantineDispositionReceipt(
        quarantine_payload=quarantine_payload,
        quarantine_topic=ack.topic,
        quarantine_partition=ack.partition,
        quarantine_offset=ack.offset,
    )


async def execute_terminal_disposition_once(
    *,
    context: ModelDeliveryContext,
    request: ModelTerminalDispositionRequest,
    publish: _AcknowledgingPublishLike,
    store: _TerminalDispositionStoreLike,
) -> ModelTerminalDispositionReceipt:
    """Replay-safe :func:`resolve_terminal_disposition`, keyed by source identity.

    Load-then-resolve-then-save. Replaying a source record after an ambiguous
    process death returns the ONE already-durable terminal receipt and publishes
    nothing further; a distinct ``source_offset`` is always a distinct event
    (OMN-15666 acceptance criterion 7).

    The residual ambiguity window — acknowledged by the broker, process died
    before ``save`` — resolves on replay to a SECOND publish and one saved
    receipt, never to two divergent terminal outcomes: the sink payload is a
    deterministic projection of the same four-field source identity, so a
    downstream quarantine consumer dedupes it on that tuple.

    ``store`` is an injected durable-persistence dependency, so both calls can
    raise a raw backend exception (a driver timeout, a connection reset). Those
    are wrapped in ``ModelOnexError`` rather than propagated untyped: an ONEX
    runtime-execution failure must surface as ``ModelOnexError`` (repo error
    convention), and a caller distinguishing "the disposition is not durable"
    from "an arbitrary driver blew up" cannot do so against an untyped
    exception. A ``save`` failure AFTER a sink acknowledged leaves the record
    uncommitted, so it redelivers and republishes — the same at-least-once
    ambiguity window described above, never a silent commit.
    """
    try:
        existing = await store.load(context)
    except ModelOnexError:
        raise
    except Exception as exc:  # boundary-ok: an injected durable store can raise ANY backend exception; it is re-raised as a typed ModelOnexError, never swallowed and never converted into a commit signal.
        raise ModelOnexError(
            message=(
                "execute_terminal_disposition_once: terminal-disposition store "
                f"load FAILED for source identity topic={context.topic!r} "
                f"partition={context.partition} offset={context.offset} "
                f"envelope_id={context.envelope_id} — refusing to treat an "
                f"unreadable store as 'no prior disposition': {exc}"
            ),
            error_code=EnumCoreErrorCode.INVALID_STATE,
        ) from exc
    if existing is not None:
        return existing

    receipt = await resolve_terminal_disposition(request=request, publish=publish)

    try:
        await store.save(context, receipt)
    except ModelOnexError:
        raise
    except Exception as exc:  # boundary-ok: same reason as the load above; the sink is already durable, but an unrecorded receipt must NOT license a commit.
        raise ModelOnexError(
            message=(
                "execute_terminal_disposition_once: terminal-disposition store "
                f"save FAILED for source identity topic={context.topic!r} "
                f"partition={context.partition} offset={context.offset} "
                f"envelope_id={context.envelope_id} — a sink acknowledged but "
                f"the receipt is NOT durable, so the source offset must not be "
                f"committed: {exc}"
            ),
            error_code=EnumCoreErrorCode.INVALID_STATE,
        ) from exc
    return receipt
