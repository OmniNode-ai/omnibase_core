# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Configure local defaults and selected authoritative backend overrides."""

from __future__ import annotations

import importlib.metadata
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from omnibase_core.handlers.handler_backend_discovery import HandlerBackendDiscovery
from omnibase_core.handlers.handler_backend_override import (
    HandlerBackendOverride,
    LocalRegistration,
)
from omnibase_core.handlers.handler_backend_selection import HandlerBackendSelection
from omnibase_core.models.container.model_auto_config_result import (
    ModelAutoConfigResult,
)

logger = logging.getLogger(__name__)

_LOCAL_BACKENDS = {"ProtocolEventBus": "inmemory", "ProtocolStateStore": "disk"}


async def auto_configure_registry(
    container: Any,
    *,
    state_root: str | Path = ".onex_state",
    pins: Mapping[str, str] | None = None,
) -> ModelAutoConfigResult:
    """Validate and stage overrides, then register defaults and replacements."""
    selected_pins = dict(pins) if pins is not None else {}
    eps = importlib.metadata.entry_points()
    backend_eps = eps.select(group="onex.backends") if hasattr(eps, "select") else []
    probes, findings = HandlerBackendDiscovery().handle(backend_eps)
    selected = HandlerBackendSelection().handle(probes, selected_pins, _LOCAL_BACKENDS)
    handler = HandlerBackendOverride()
    instances, stage_findings = handler.handle(selected, selected_pins, _LOCAL_BACKENDS)
    findings.extend(stage_findings)
    registry = container.service_registry
    defaults = await _register_local_defaults(registry, state_root=Path(state_root))
    overrides, registration_findings = await handler.register(
        registry, defaults, selected, instances
    )
    findings.extend(registration_findings)
    return ModelAutoConfigResult(findings=tuple(findings), overrides=overrides)


async def _register_local_defaults(
    registry: Any,
    *,
    state_root: Path,
) -> dict[str, LocalRegistration]:
    """Register local defaults, retaining registration IDs and interface types."""
    from omnibase_core.protocols.event_bus.protocol_event_bus import ProtocolEventBus

    defaults: dict[str, LocalRegistration] = {}
    try:
        from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory

        bus = EventBusInmemory()
        registration_id = await registry.register_instance(ProtocolEventBus, bus)
        defaults["ProtocolEventBus"] = (registration_id, ProtocolEventBus)
        logger.info("EventBus: in-memory (source: default, package: omnibase_core)")
    except ImportError:
        logger.debug("EventBusInmemory not available — skipping local bus default")

    try:
        from omnibase_core.protocols.storage.protocol_state_store import (
            ProtocolStateStore,
        )
        from omnibase_core.services.state.service_state_disk import ServiceStateDisk

        store = ServiceStateDisk(state_root=state_root)
        registration_id = await registry.register_instance(ProtocolStateStore, store)
        defaults["ProtocolStateStore"] = (registration_id, ProtocolStateStore)
        logger.info("StateStore: disk (source: default, package: omnibase_core)")
    except ImportError:
        logger.debug("ServiceStateDisk not available — skipping local state default")

    return defaults
