# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Adapter bridging ONEX handlers to the in-memory event bus."""

from __future__ import annotations

__all__ = ["LocalRuntimeBusAdapter"]

import inspect
import json
import logging
import os
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import cast
from uuid import UUID, uuid4, uuid5

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
    ProtocolLocalRuntimeCallableTarget,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
    ProtocolLocalRuntimeMessage,
)
from omnibase_core.runtime.runtime_fanout_resolver import (
    is_fanout_sequence,
    resolve_fanout_emissions,
    resolve_published_topic,
)

logger = logging.getLogger(__name__)

# OMN-14403 §6ii — the def-B multi-event (fan-out) publish seam. Default OFF; the
# canonical read on the Kafka path lives in
# ``omnibase_infra.runtime.auto_wiring.handler_wiring`` — this is the mirror read
# for the RuntimeLocal path so both runtimes gate on the same flag (Fable
# refinement 3 / parity). While OFF the adapter's behavior is byte-for-byte
# today's for single-emit/None returns; a fan-out sequence is warn-dropped (the
# census channel that names affected handlers in live logs), never published.
ENV_MULTI_EVENT_PUBLISH_SEAM = "ONEX_MULTI_EVENT_PUBLISH_SEAM"


def multi_event_publish_seam_enabled() -> bool:
    """Return True when the def-B fan-out publish seam is enabled (default: False)."""
    return (
        os.environ.get(  # env-var-ok: OMN-14403 def-B fan-out seam; mirrors the canonical omnibase_infra handler_wiring read
            ENV_MULTI_EVENT_PUBLISH_SEAM, ""
        )
        .strip()
        .lower()
        in (
            "1",
            "true",
            "yes",
            "on",
        )
    )


class LocalRuntimeBusAdapter:
    """Wraps an ONEX handler with event bus serialization/deserialization.

    Typed handlers are invoked with the validated input model as the sole
    request object. Legacy handlers that explicitly accept **kwargs are invoked
    with model.model_dump() as kwargs.
    Results are serialized to JSON and published to the output topic.
    Correlation IDs are preserved across input -> output.

    A def-B handler may return a ``Sequence[BaseModel]`` (fan-out) or a single
    ``BaseModel`` whose topic is resolved from the contract's ``published_events``
    class -> topic map (OMN-14403 §6ii). Both go through the shared
    ``runtime_fanout_resolver`` so this path and the Kafka path agree on what is
    published. This behavior is gated by ``multi_event_seam_enabled`` (default
    OFF); when OFF, single-emit/None returns are unchanged and a fan-out sequence
    is warn-dropped.

    On handler error: logs the exception, sets the workflow terminal event
    to FAILED, and does NOT publish output.
    """

    def __init__(
        self,
        handler: ProtocolLocalRuntimeCallableTarget,
        handler_name: str,
        input_model_cls: type[BaseModel] | None,
        output_topic: str | None,
        bus: ProtocolLocalRuntimeBus,
        on_error: Callable[[], None] | None = None,
        on_result: Callable[[object], None] | None = None,
        published_events: Mapping[str, str] | None = None,
        multi_event_seam_enabled: bool = False,
    ) -> None:
        self.handler = handler
        self.handler_name = handler_name
        # None when the routing entry declares no payload model — operation_match
        # entries route by `operation`, not a typed event model (OMN-13141). The
        # raw decoded dict is forwarded to the handler in that case.
        self.input_model_cls = input_model_cls
        self.output_topic = output_topic
        self.bus = bus
        self.on_error = on_error
        self.on_result = on_result
        # OMN-14403 §6ii: the contract's published_events class -> topic map. When
        # present (and the seam is ON), a returned event's topic is resolved from
        # its class via this map instead of the single ``output_topic`` — the only
        # correct routing for a multi-topic / fan-out ORCHESTRATOR whose emitted
        # class varies per phase. None/empty keeps the single-``output_topic`` path.
        self.published_events: Mapping[str, str] = published_events or {}
        self.multi_event_seam_enabled = multi_event_seam_enabled

    async def on_message(self, msg: ProtocolLocalRuntimeMessage) -> None:
        """Receive bus message, invoke handler, publish result."""
        # 1. Deserialize
        correlation_id: str | None = None
        try:
            decoded: object = (
                json.loads(msg.value) if isinstance(msg.value, bytes) else {}
            )
            decoded_dict = decoded if isinstance(decoded, dict) else {}
            # A fan-out emit is published as a ``ModelEventEnvelope`` carrying the
            # topic-derived ``event_type`` (OMN-14743) so a cross-process
            # type-scoped dispatcher matches it. Unwrap to the inner domain
            # ``payload`` before validating into ``input_model_cls`` — a raw
            # (non-enveloped) message passes through unchanged. ``envelope_id`` is
            # the discriminator: a domain payload (e.g. ModelRoutingIntent, which
            # itself has a ``payload`` field) never carries ``envelope_id``.
            payload_dict, envelope_correlation = _unwrap_envelope_dict(decoded_dict)
            correlation_value = envelope_correlation or payload_dict.get(
                "correlation_id"
            )
            correlation_id = (
                correlation_value if isinstance(correlation_value, str) else None
            )
            # operation_match entries declare no payload model (OMN-13141): forward
            # the raw decoded dict. payload_type_match validates against the model.
            # Typed `object` (model or dict) — helpers narrow with isinstance.
            input_payload: object = (
                self.input_model_cls(**payload_dict)
                if self.input_model_cls is not None
                else payload_dict
            )
        except Exception:  # fallback-ok: local runtime adapter records handler failure and continues shutdown
            logger.exception(
                "LocalRuntimeBusAdapter: deserialization failed for %s (correlation_id=%s)",
                self.handler_name,
                correlation_id,
            )
            if self.on_error:
                self.on_error()
            return

        # 2. Invoke handler
        logger.info(
            "LocalRuntimeBusAdapter: invoking %s (correlation_id=%s)",
            self.handler_name,
            correlation_id,
        )
        start = time.monotonic()
        try:
            handle_method = self.handler.handle
            maybe_result = _invoke_handle_method(handle_method, input_payload)
            if inspect.isawaitable(maybe_result):
                awaitable_result: Awaitable[object] = cast(
                    "Awaitable[object]", maybe_result
                )
                result = await awaitable_result
            else:
                result = maybe_result
        except Exception:  # fallback-ok: local runtime adapter records handler failure and continues shutdown
            elapsed = time.monotonic() - start
            logger.exception(
                "LocalRuntimeBusAdapter: %s raised after %.2fs (correlation_id=%s)",
                self.handler_name,
                elapsed,
                correlation_id,
            )
            if self.on_error:
                self.on_error()
            return

        elapsed = time.monotonic() - start
        logger.info(
            "LocalRuntimeBusAdapter: %s completed in %.2fs (correlation_id=%s)",
            self.handler_name,
            elapsed,
            correlation_id,
        )

        # 3. Publish output
        if result is None:
            return
        if self.on_result:
            self.on_result(result)

        # 3a. def-B fan-out (Sequence[BaseModel]) — OMN-14403 §6ii. Each element's
        # topic is resolved from the contract's published_events and one message
        # is published per element, so a multi-topic ORCHESTRATOR is representable.
        # While the seam is OFF the sequence is warn-dropped (the census channel)
        # rather than published — no longer silent, but no behavior change either.
        if is_fanout_sequence(result):
            await self._publish_fanout(cast("Sequence[object]", result), correlation_id)
            return

        # 3b. Single-emit.
        try:
            output_topic = self._resolve_single_emit_topic(result)
            if output_topic is None:
                return
            if isinstance(result, BaseModel):
                output_bytes = result.model_dump_json().encode("utf-8")
            elif isinstance(result, dict):
                output_bytes = json.dumps(result).encode("utf-8")
            else:
                raise ModelOnexError(
                    message=(
                        f"LocalRuntimeBusAdapter: handler {self.handler.__class__.__name__!r}"
                        f" returned unsupported type {type(result).__name__!r};"
                        " expected BaseModel, Sequence[BaseModel], dict, or None"
                    ),
                    error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                )
            await self.bus.publish(output_topic, None, output_bytes)
            logger.info(
                "LocalRuntimeBusAdapter: published to %s (correlation_id=%s)",
                output_topic,
                correlation_id,
            )
        except Exception:  # fallback-ok: publish failure is recorded via on_error and the run is marked FAILED; reraising here would mask the workflow result and abort the bus shutdown
            logger.exception(
                "LocalRuntimeBusAdapter: publish failed for %s -> %s (correlation_id=%s)",
                self.handler_name,
                self.output_topic,
                correlation_id,
            )
            if self.on_error:
                self.on_error()

    def _resolve_single_emit_topic(self, result: object) -> str | None:
        """Resolve the topic for a single-emit result, or None to publish nothing.

        A ``BaseModel`` routes via the contract's ``published_events`` when the seam
        is ON and the contract declares one (the per-phase orchestrator case, whose
        emitted class varies per phase and so cannot use a single ``output_topic``);
        otherwise it falls back to ``output_topic``. Fail-closed: an unmapped class
        under an active published_events map raises rather than misrouting. A dict
        keeps the legacy ``output_topic`` path.
        """
        if (
            isinstance(result, BaseModel)
            and self.multi_event_seam_enabled
            and self.published_events
        ):
            return resolve_published_topic(
                self.published_events, result, message_type=self.handler_name
            )
        return self.output_topic or None

    async def _publish_fanout(
        self, elements: Sequence[object], correlation_id: str | None
    ) -> None:
        """Publish a def-B fan-out sequence, one message per resolved topic (§6ii).

        Seam OFF: warn-drop the sequence (census channel), publish nothing — the
        pre-seam behavior for wired handlers, now visible in logs. Seam ON: resolve
        each element's topic via the shared resolver (fail-closed on unmapped /
        carrier) and publish N messages in return order.
        """
        if not self.multi_event_seam_enabled:
            if elements:
                logger.warning(
                    "LocalRuntimeBusAdapter: handler %s returned a %d-element "
                    "sequence which is being DROPPED (not published) — set %s=1 to "
                    "publish it as a fan-out batch (OMN-14403). element_types=%s "
                    "(correlation_id=%s)",
                    self.handler_name,
                    len(elements),
                    ENV_MULTI_EVENT_PUBLISH_SEAM,
                    sorted({type(element).__name__ for element in elements}),
                    correlation_id,
                )
            return
        try:
            # Resolve (topic, event_type, payload) triples. ``resolve_fanout_emissions``
            # is FAIL-CLOSED on a topic that yields no derivable event_type — an
            # emitted fan-out envelope with a null event_type is silently dropped by
            # the consuming type-scoped dispatcher (the OMN-14743 stall). Order is
            # the handler's return order.
            emissions = resolve_fanout_emissions(
                self.published_events, elements, message_type=self.handler_name
            )
            correlation_uuid = _coerce_correlation_uuid(correlation_id)
            for idx, (topic, event_type, payload) in enumerate(emissions):
                envelope = self._build_output_envelope(
                    payload, event_type, correlation_uuid, idx
                )
                output_bytes = envelope.model_dump_json().encode("utf-8")
                await self.bus.publish(topic, None, output_bytes)
                logger.info(
                    "LocalRuntimeBusAdapter: fan-out published %s to %s "
                    "(event_type=%s correlation_id=%s)",
                    type(payload).__name__,
                    topic,
                    event_type,
                    correlation_id,
                )
        except Exception:  # fallback-ok: fan-out resolution/publish failure is recorded via on_error and the run is marked FAILED; reraising would abort bus shutdown
            logger.exception(
                "LocalRuntimeBusAdapter: fan-out publish failed for %s (correlation_id=%s)",
                self.handler_name,
                correlation_id,
            )
            if self.on_error:
                self.on_error()

    def _build_output_envelope(
        self,
        payload: BaseModel,
        event_type: str,
        correlation_uuid: UUID | None,
        idx: int,
    ) -> ModelEventEnvelope[BaseModel]:
        """Wrap a fan-out payload in an event envelope carrying ``event_type``.

        Mirrors the Kafka applier's envelope shape
        (``service_dispatch_result_applier.apply``): a deterministic
        ``uuid5(correlation_id, "type:index")`` envelope_id so a redelivery
        dedupes, and the topic-derived ``event_type`` routing key so a
        type-scoped dispatcher matches (OMN-14743). When no correlation_id is
        available the envelope_id falls back to ``uuid4`` (dedup is best-effort,
        matching the applier).
        """
        envelope_id = (
            uuid5(correlation_uuid, f"{type(payload).__name__}:{idx}")
            if correlation_uuid is not None
            else uuid4()
        )
        # Construct WITHOUT the ``[BaseModel]`` runtime subscript: subscripting the
        # generic at runtime coerces the payload to the bare ``BaseModel`` schema and
        # drops the concrete model's fields on ``model_dump_json`` (payload -> {}).
        # The applier constructs the same way (annotate the var, not the call).
        envelope: ModelEventEnvelope[BaseModel] = ModelEventEnvelope(
            envelope_id=envelope_id,
            payload=payload,
            correlation_id=correlation_uuid,
            event_type=event_type,
        )
        return envelope


def _coerce_correlation_uuid(correlation_id: str | None) -> UUID | None:
    """Coerce a wire correlation_id string into a UUID, or None when unparseable."""
    if not correlation_id:
        return None
    try:
        return UUID(correlation_id)
    except (ValueError, AttributeError, TypeError):
        return None


def _unwrap_envelope_dict(
    decoded: Mapping[str, object],
) -> tuple[dict[str, object], str | None]:
    """Unwrap a ``ModelEventEnvelope`` wire dict to its inner payload dict.

    Returns ``(payload_dict, correlation_id)``. A fan-out emit publishes a
    ``ModelEventEnvelope`` (OMN-14743); the inner domain ``payload`` is what the
    subscribed handler's ``input_model_cls`` validates against. ``envelope_id`` is
    the discriminator — a raw (non-enveloped) message, or a domain payload that
    happens to carry its own ``payload`` field (e.g. ModelRoutingIntent), lacks
    ``envelope_id`` and is returned unchanged.
    """
    if "envelope_id" in decoded and isinstance(decoded.get("payload"), dict):
        inner = cast("dict[str, object]", decoded["payload"])
        correlation = decoded.get("correlation_id")
        return inner, correlation if isinstance(correlation, str) else None
    return dict(decoded), None


def _invoke_handle_method(
    handle_method: Callable[..., object],
    input_payload: object,
) -> object:
    """Invoke a local-runtime handler using its declared calling convention.

    ``input_payload`` is a validated model for payload_type_match entries, or the
    raw decoded dict for operation_match entries that declare no payload model
    (OMN-13141). Keyword-fanout uses ``model_dump`` for models and the dict
    directly; single-model-parameter handlers receive the object itself.

    When the handler's sole positional parameter is annotated with a concrete
    ``BaseModel`` subclass but ``input_payload`` is still the raw decoded dict
    (the operation_match case — no contract-declared event model to validate
    against upstream), the dict is validated into that annotated type here
    before the call (OMN-8724). Without this coercion a typed single-parameter
    handler such as ``handle(self, request: GoldenChainSweepRequest)`` receives
    a bare ``dict`` and crashes on the first attribute access. This is the
    systemic fix for the dict-not-typed dispatch-boundary class (same family as
    OMN-13141 / the savings_estimation ``.get()`` bug).
    """
    kwargs: dict[str, object] = (
        input_payload.model_dump(mode="json")
        if isinstance(input_payload, BaseModel)
        else input_payload
        if isinstance(input_payload, dict)
        else {}
    )
    # eval_str=True resolves PEP 563 string annotations (``from __future__ import
    # annotations`` is used by every node handler, so without this the parameter
    # annotation is the literal string "GoldenChainSweepRequest" and the
    # BaseModel-subclass check below never matches — the OMN-8724 root cause).
    try:
        signature = inspect.signature(handle_method, eval_str=True)
    except (TypeError, ValueError, NameError):
        # NameError: an annotation referenced a name not importable in the
        # handler module globals. Fall back to unevaluated annotations rather
        # than aborting dispatch.
        try:  # fallback-ok: eval_str signature introspection failed; retry without annotation evaluation so dispatch still adapts the call rather than aborting
            signature = inspect.signature(handle_method)
        except (TypeError, ValueError):
            return handle_method(input_payload)

    parameters = tuple(signature.parameters.values())
    if any(param.kind is inspect.Parameter.VAR_KEYWORD for param in parameters):
        return handle_method(**kwargs)

    positional_parameters = tuple(
        param
        for param in parameters
        if param.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    )
    if len(positional_parameters) == 0:
        return handle_method()

    if len(positional_parameters) == 1:
        model_type = _coercion_target_model_type(
            positional_parameters[0],
            input_payload,
        )
        if model_type is not None:
            # Annotation is a concrete BaseModel subclass and the payload is a
            # raw dict: validate the dict into the declared type before calling.
            return handle_method(model_type.model_validate(input_payload))
        if _parameter_expects_model(positional_parameters[0], input_payload):
            return handle_method(input_payload)

    return handle_method(**kwargs)


def _coercion_target_model_type(
    parameter: inspect.Parameter,
    input_payload: object,
) -> type[BaseModel] | None:
    """Return the annotated ``BaseModel`` subclass to coerce a raw dict payload into.

    Returns ``None`` unless ``input_payload`` is a raw ``dict`` and the
    parameter's annotation is a concrete ``BaseModel`` subclass. This is the only
    coercion trigger (OMN-8724): a real annotation, not a parameter-name
    heuristic, drives it — so a model-typed single-parameter handler reached via
    ``operation_match`` (no upstream event-model validation) gets a validated
    model instead of the raw dict that previously crashed it.
    """
    if not isinstance(input_payload, dict):
        return None
    annotation = parameter.annotation
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _parameter_expects_model(
    parameter: inspect.Parameter,
    input_payload: object,
) -> bool:
    """Return True when a single handle parameter should receive the payload object.

    Only reached after dict→model coercion has been considered
    (``_coercion_target_model_type``), so this governs the already-a-model and
    name-heuristic pass-through paths that pre-date OMN-8724.
    """
    if parameter.name in {"request", "payload", "event", "input_model"}:
        return True

    annotation = parameter.annotation
    return (
        isinstance(input_payload, BaseModel)
        and isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
        and issubclass(type(input_payload), annotation)
    )
