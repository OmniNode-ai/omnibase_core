# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validate pins and select unambiguous authoritative backend probes."""

from __future__ import annotations

from collections.abc import Mapping

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_probe_state import EnumProbeState
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_backend_discovery import (
    BackendProbes,
    ProbedBackend,
)


class HandlerBackendSelection:
    """Select at most one authoritative backend per protocol without side effects."""

    def handle(
        self,
        probes: BackendProbes,
        pins: Mapping[str, str],
        local_backends: Mapping[str, str],
    ) -> dict[str, ProbedBackend]:
        """Reject absent or nonauthoritative pins and ambiguous selections."""
        selected: dict[str, ProbedBackend] = {}
        for proto_name in sorted(probes.keys() | pins.keys()):
            backends = probes.get(proto_name, {})
            if proto_name in pins:
                backend_name = pins[proto_name]
                if proto_name not in local_backends and proto_name not in probes:
                    raise ModelOnexError(
                        message=f"Unknown protocol {proto_name} pinned to {backend_name}",
                        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    )
                if backend_name == local_backends.get(proto_name):
                    continue
                candidates = backends.get(backend_name, [])
                if not candidates:
                    raise ModelOnexError(
                        message=f"Pinned backend {backend_name} for {proto_name} is absent",
                        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    )
            else:
                candidates = [
                    backend for group in backends.values() for backend in group
                ]

            authoritative = [
                backend
                for backend in candidates
                if backend[2].state == EnumProbeState.AUTHORITATIVE
            ]
            if not authoritative and proto_name in pins:
                raise ModelOnexError(
                    message=(
                        f"Pinned backend {pins[proto_name]} for {proto_name} "
                        "is not authoritative"
                    ),
                    error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                )
            if len(authoritative) > 1:
                names = ", ".join(
                    sorted(backend[2].backend_name for backend in authoritative)
                )
                raise ModelOnexError(
                    message=(
                        f"Multiple authoritative backends for {proto_name}: {names}. "
                        f"Specify --backend {proto_name.lower()}=<choice>"
                    ),
                    error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                )
            if authoritative:
                selected[proto_name] = authoritative[0]

        return selected
