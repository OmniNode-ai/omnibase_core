# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Stage backend instances and apply overrides after local registration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_backend_finding_reason import EnumBackendFindingReason
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_backend_discovery import ProbedBackend
from omnibase_core.models.container.model_backend_finding import ModelBackendFinding
from omnibase_core.models.container.model_probe_result import ModelProbeResult

logger = logging.getLogger(__name__)

type LocalRegistration = tuple[UUID, type[object]]
type BackendInstances = dict[str, tuple[object, ModelProbeResult]]


class HandlerBackendOverride:
    """Construct selected backends before registry mutation, then apply them."""

    def handle(
        self,
        selected: Mapping[str, ProbedBackend],
        pins: Mapping[str, str],
        local_backends: Mapping[str, str],
    ) -> tuple[BackendInstances, list[ModelBackendFinding]]:
        """Stage instances, refusing pinned failures before registering defaults."""
        findings: list[ModelBackendFinding] = []
        instances: BackendInstances = {}
        for proto_name, (ep, backend_cls, result) in selected.items():
            if proto_name not in local_backends:
                if proto_name in pins:
                    raise ModelOnexError(
                        message=(
                            f"Pinned backend {result.backend_name} for {proto_name} "
                            "has no local interface to replace"
                        ),
                        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    )
                findings.append(
                    ModelBackendFinding(
                        entry_point=ep.name,
                        value=ep.value,
                        reason=EnumBackendFindingReason.UNKNOWN_PROTOCOL,
                        detail=f"No local interface for {proto_name}",
                    )
                )
                continue

            try:
                instance = backend_cls()
            except (TypeError, ValueError, OSError, ModelOnexError) as exc:
                findings.append(
                    ModelBackendFinding(
                        entry_point=ep.name,
                        value=ep.value,
                        reason=EnumBackendFindingReason.NOT_INSTANTIABLE,
                        detail=str(exc),
                    )
                )
                logger.warning(
                    "Cannot instantiate entry point %s", ep.name, exc_info=True
                )
                if proto_name in pins:
                    raise ModelOnexError(
                        message=(
                            f"Pinned backend {result.backend_name} for {proto_name} "
                            f"could not be instantiated: {exc}"
                        ),
                        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    ) from exc
                continue
            instances[proto_name] = (instance, result)

        return instances, findings

    async def register(
        self,
        registry: Any,
        defaults: Mapping[str, LocalRegistration],
        selected: Mapping[str, ProbedBackend],
        instances: BackendInstances,
    ) -> tuple[dict[str, str], list[ModelBackendFinding]]:
        """Replace registered defaults and report unavailable local interfaces."""
        findings: list[ModelBackendFinding] = []
        overrides: dict[str, str] = {}
        for proto_name, (instance, result) in instances.items():
            local = defaults.get(proto_name)
            if local is None:
                # An unavailable local implementation also leaves no registered interface.
                ep = selected[proto_name][0]
                findings.append(
                    ModelBackendFinding(
                        entry_point=ep.name,
                        value=ep.value,
                        reason=EnumBackendFindingReason.UNKNOWN_PROTOCOL,
                        detail=f"No local registration for {proto_name}",
                    )
                )
                continue
            registration_id, interface = local
            await registry.unregister_service(registration_id)
            await registry.register_instance(interface, instance)
            overrides[proto_name] = result.backend_name
            logger.info(
                "Override registered: %s → %s (package: %s)",
                proto_name,
                result.backend_name,
                result.package,
            )

        return overrides, findings
