# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Adapter bridging ONEX handlers to the in-memory event bus."""

from __future__ import annotations

__all__ = ["LocalRuntimeBusAdapter"]

import inspect
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import cast

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
    ProtocolLocalRuntimeCallableTarget,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
    ProtocolLocalRuntimeMessage,
)

logger = logging.getLogger(__name__)


class LocalRuntimeBusAdapter:
    """Wraps an ONEX handler with event bus serialization/deserialization.

    Typed handlers are invoked with the validated input model as the sole
    request object. Legacy handlers that explicitly accept **kwargs are invoked
    with model.model_dump() as kwargs.
    Results are serialized to JSON and published to the output topic.
    Correlation IDs are preserved across input -> output.

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

    async def on_message(self, msg: ProtocolLocalRuntimeMessage) -> None:
        """Receive bus message, invoke handler, publish result."""
        # 1. Deserialize
        correlation_id: str | None = None
        try:
            decoded: object = (
                json.loads(msg.value) if isinstance(msg.value, bytes) else {}
            )
            payload_dict = decoded if isinstance(decoded, dict) else {}
            correlation_value = payload_dict.get("correlation_id")
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
        if not self.output_topic:
            return
        try:
            if isinstance(result, BaseModel):
                output_bytes = result.model_dump_json().encode("utf-8")
            elif isinstance(result, dict):
                output_bytes = json.dumps(result).encode("utf-8")
            else:
                raise ModelOnexError(
                    message=(
                        f"LocalRuntimeBusAdapter: handler {self.handler.__class__.__name__!r}"
                        f" returned unsupported type {type(result).__name__!r};"
                        " expected BaseModel, dict, or None"
                    ),
                    error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                )
            await self.bus.publish(self.output_topic, None, output_bytes)
            logger.info(
                "LocalRuntimeBusAdapter: published to %s (correlation_id=%s)",
                self.output_topic,
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
