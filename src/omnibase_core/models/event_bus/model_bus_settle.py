# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Settle a runtime-local run's bus: carry its recorded events where its binding says (OMN-24000).

``RuntimeLocal`` resolves to the in-memory bus when nothing overrides it, and the events of an
in-memory bus die with the process. This is the one place the runtime reads what its bus recorded
and either hands it to the forwarder the binding names (a runtime-local in-memory bus whose
forwarder carries its events to the hosted bus), records that nothing needed carrying (hosted bus;
a bus a test declared), or raises the degraded alarm (no binding at all, an in-memory bus with no
forwarder, a forward that failed). The alarm is an error log record and one stderr line; the
reading goes into ``workflow_result.json`` under ``bus_reading``. Nothing here changes a run's
result: the run is finished when its bus is settled.

The binding is the run's ``backend_overrides``: no ``event_bus`` key is no declaration (UNKNOWN),
``event_bus=kafka`` is the hosted bus, ``event_bus=inmemory`` declares an in-memory runtime whose
forwarder is the one installed under ``onex.runtime_bus_forwarders``, and ``forwarder=none``
beside it declares a bus a test keeps to itself. The canonical-file-shape ratchet lets
``runtime_local.py`` only shrink and admits no handler outside a node, so the behaviour lives with
the models it reads; the forwarder is registered by the package that can reach the hosted bus and
core never imports it (compat -> core -> spi -> infra layering).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Mapping

from omnibase_core.enums.enum_runtime_bus_binding_kind import EnumRuntimeBusBindingKind
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_runtime_bus_binding import (
    ModelRuntimeBusBinding,
)
from omnibase_core.models.event_bus.model_runtime_bus_event import ModelRuntimeBusEvent
from omnibase_core.models.event_bus.model_runtime_bus_forward_receipt import (
    ModelRuntimeBusForwardReceipt,
)
from omnibase_core.models.event_bus.model_runtime_bus_reading import (
    ModelRuntimeBusReading,
)

logger = logging.getLogger("omnibase_core.runtime.runtime_local")

# What a forwarder may fail with: its own refusal (ModelOnexError), the transport (OSError), a
# receipt that does not validate (ValueError), a registration that does not load (ImportError,
# LookupError) or a bug in a plugin (TypeError, RuntimeError). Each is recorded as a degraded
# reading; none ends the finished run.
_FORWARD_FAILURES = (
    ModelOnexError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    ImportError,
    LookupError,
)


class ModelBusSettle:
    """Namespace of the bus-settle steps ``RuntimeLocal`` runs when its bus is about to close."""

    @staticmethod
    def binding_from_overrides(
        backend_overrides: Mapping[str, str],
    ) -> ModelRuntimeBusBinding:
        """The binding a run's ``backend_overrides`` declare; UNKNOWN when they declare none."""
        declared = backend_overrides.get("event_bus")
        if declared == "kafka":
            return ModelRuntimeBusBinding.hosted()
        if declared == "inmemory":
            if backend_overrides.get("forwarder") == "none":
                return ModelRuntimeBusBinding.test()
            return ModelRuntimeBusBinding.declared_inmemory()
        return ModelRuntimeBusBinding.unknown(
            "no bus binding was declared for this runtime; it uses the in-memory bus "
            "and its events go nowhere"
        )

    @staticmethod
    def read(
        binding: ModelRuntimeBusBinding, events: tuple[ModelRuntimeBusEvent, ...]
    ) -> ModelRuntimeBusReading:
        """What ``binding`` did with ``events``: forwarded, nothing to carry, or degraded. Blocking."""
        kind = binding.kind
        if kind is EnumRuntimeBusBindingKind.HOSTED:
            return ModelRuntimeBusReading(kind=kind, degraded=False, events_recorded=0)
        if kind is not EnumRuntimeBusBindingKind.INMEMORY_FORWARDED:
            return ModelRuntimeBusReading(
                kind=kind,
                degraded=kind.is_degraded,
                reason=binding.reason,
                events_recorded=len(events),
                events_failed=len(events) if kind.is_degraded else 0,
            )
        if not events:
            return ModelRuntimeBusReading(
                kind=kind,
                forwarder=binding.forwarder,
                degraded=False,
                events_recorded=0,
            )
        try:
            receipt = ModelRuntimeBusForwardReceipt.model_validate(
                binding.load_forward()(events), from_attributes=True
            )
        except _FORWARD_FAILURES as exc:
            return ModelRuntimeBusReading(
                kind=kind,
                forwarder=binding.forwarder,
                degraded=True,
                reason=f"forwarder {binding.forwarder} failed: {type(exc).__name__}: {exc}",
                events_recorded=len(events),
                events_failed=len(events),
            )
        return ModelRuntimeBusReading(
            kind=kind,
            forwarder=binding.forwarder,
            degraded=receipt.failed > 0,
            reason=receipt.detail,
            events_recorded=len(events),
            events_forwarded=receipt.forwarded,
            events_failed=receipt.failed,
        )

    @staticmethod
    def announce(reading: ModelRuntimeBusReading) -> None:
        """Say so loudly when the reading is degraded: an error log record and one stderr line."""
        if not reading.degraded:
            logger.info(
                "RuntimeLocal bus reading: kind=%s recorded=%d forwarded=%d",
                reading.kind.value,
                reading.events_recorded,
                reading.events_forwarded,
            )
            return
        logger.error(
            "RuntimeLocal DEGRADED BUS: kind=%s reason=%s recorded=%d not_delivered=%d",
            reading.kind.value,
            reading.reason,
            reading.events_recorded,
            reading.events_failed,
        )
        sys.stderr.write(
            f"RuntimeLocal DEGRADED BUS ({reading.kind.value}): {reading.reason}; "
            f"{reading.events_recorded} event(s) recorded, "
            f"{reading.events_failed} not delivered\n"
        )

    @staticmethod
    async def settle(
        bus: object, backend_overrides: Mapping[str, str]
    ) -> ModelRuntimeBusReading:
        """Settle ``bus`` by the run's declared binding before it closes; announce and return the reading."""
        binding = ModelBusSettle.binding_from_overrides(backend_overrides)
        get_history = getattr(bus, "get_event_history", None)
        history = (
            await get_history(limit=sys.maxsize)
            if get_history is not None
            and binding.kind is not EnumRuntimeBusBindingKind.HOSTED
            else ()
        )
        events = tuple(ModelRuntimeBusEvent.from_message(m) for m in history)
        reading = await asyncio.to_thread(ModelBusSettle.read, binding, events)
        ModelBusSettle.announce(reading)
        return reading


__all__ = ["ModelBusSettle"]
