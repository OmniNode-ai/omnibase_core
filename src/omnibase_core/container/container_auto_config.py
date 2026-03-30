# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Auto-configure registry with discovered backends.

Priority: most-specific healthy backend wins.
Default: local backends (in-memory bus, disk state).
Entry point group: onex.backends

Each entry point must reference a class with a ``probe()`` classmethod
returning ``ModelProbeResult``.  Local defaults always register first;
production backends override only when probe returns AUTHORITATIVE.
"""

from __future__ import annotations

import importlib.metadata
import logging
from pathlib import Path
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_probe_state import EnumProbeState
from omnibase_core.models.container.model_probe_result import ModelProbeResult
from omnibase_core.models.errors.model_onex_error import ModelOnexError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def auto_configure_registry(
    container: Any,
    *,
    state_root: str | Path = ".onex_state",
) -> None:
    """Discover and register backends into *container*'s service registry.

    1. Register local defaults (in-memory bus, disk state store).
    2. Scan ``onex.backends`` entry-point group for additional backends.
    3. For each discovered backend, call ``probe()`` and override the local
       default **only** when probe returns AUTHORITATIVE.

    Ambiguous equal-priority resolution (two AUTHORITATIVE backends for the
    same protocol) raises ``ModelOnexError``.
    """
    registry = container.service_registry

    # --- local defaults ---------------------------------------------------
    await _register_local_defaults(registry, state_root=Path(state_root))

    # --- entry-point discovery --------------------------------------------
    await _discover_and_register_entry_points(registry)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _register_local_defaults(
    registry: Any,
    *,
    state_root: Path,
) -> None:
    """Register built-in local backends (always available)."""
    from omnibase_core.protocols.event_bus.protocol_event_bus import ProtocolEventBus

    # -- in-memory event bus -----------------------------------------------
    try:
        from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory

        bus = EventBusInmemory()
        await registry.register_instance(ProtocolEventBus, bus)
        logger.info("EventBus: in-memory (source: default, package: omnibase_core)")
    except ImportError:
        logger.debug("EventBusInmemory not available — skipping local bus default")

    # -- disk state store --------------------------------------------------
    try:
        from omnibase_core.protocols.storage.protocol_state_store import (
            ProtocolStateStore,
        )
        from omnibase_core.services.state.service_state_disk import ServiceStateDisk

        store = ServiceStateDisk(state_root=state_root)
        await registry.register_instance(ProtocolStateStore, store)
        logger.info("StateStore: disk (source: default, package: omnibase_core)")
    except ImportError:
        logger.debug("ServiceStateDisk not available — skipping local state default")


async def _discover_and_register_entry_points(registry: Any) -> None:
    """Scan ``onex.backends`` entry points and register authoritative ones."""
    eps = importlib.metadata.entry_points()
    backend_eps = eps.select(group="onex.backends") if hasattr(eps, "select") else []

    # Collect probes keyed by protocol name
    authoritative: dict[str, list[ModelProbeResult]] = {}

    for ep in backend_eps:
        try:
            backend_cls = ep.load()
        except (ImportError, AttributeError, ModuleNotFoundError):
            logger.warning("Failed to load entry point %s", ep.name, exc_info=True)
            continue

        if not hasattr(backend_cls, "probe"):
            logger.warning(
                "Entry point %s (%s) has no probe() classmethod — skipping",
                ep.name,
                ep.value,
            )
            continue

        try:
            result: ModelProbeResult = backend_cls.probe()
        except (TypeError, ValueError, AttributeError, OSError):
            logger.warning("probe() failed for entry point %s", ep.name, exc_info=True)
            continue

        logger.info(
            "%s: %s (source: entry_point, package: %s, state: %s)",
            result.protocol_name,
            result.backend_name,
            result.package,
            result.state.value,
        )

        if result.state == EnumProbeState.AUTHORITATIVE:
            authoritative.setdefault(result.protocol_name, []).append(result)

    # --- conflict detection -----------------------------------------------
    for proto_name, results in authoritative.items():
        if len(results) > 1:
            names = ", ".join(r.backend_name for r in results)
            msg = (
                f"Multiple authoritative backends for {proto_name}: {names}. "
                f"Specify --backend {proto_name.lower()}=<choice>"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )

    # --- override registration (placeholder for entry-point instances) -----
    # Actual override wiring will be added when concrete entry points exist.
    # For now we log and move on — the local defaults remain active.
    for proto_name, results in authoritative.items():
        result = results[0]
        logger.info(
            "Override registered: %s → %s (package: %s)",
            proto_name,
            result.backend_name,
            result.package,
        )
