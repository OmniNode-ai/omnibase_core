# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Discover and probe backend entry points in stable order."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from importlib.metadata import EntryPoint

from omnibase_core.enums.enum_backend_finding_reason import EnumBackendFindingReason
from omnibase_core.models.container.model_backend_finding import ModelBackendFinding
from omnibase_core.models.container.model_probe_result import ModelProbeResult

logger = logging.getLogger(__name__)

type ProbedBackend = tuple[EntryPoint, Callable[[], object], ModelProbeResult]
type BackendProbes = dict[str, dict[str, list[ProbedBackend]]]


class HandlerBackendDiscovery:
    """Load entry points and collect probes and skipped-backend findings."""

    def handle(
        self, entry_points: Iterable[EntryPoint]
    ) -> tuple[BackendProbes, list[ModelBackendFinding]]:
        """Return probes grouped by protocol and backend, plus diagnostics."""
        findings: list[ModelBackendFinding] = []
        probes: BackendProbes = {}

        for ep in sorted(entry_points, key=lambda entry: (entry.name, entry.value)):
            try:
                backend_cls = ep.load()
            except (ImportError, AttributeError, ModuleNotFoundError) as exc:
                logger.warning("Failed to load entry point %s", ep.name, exc_info=True)
                findings.append(
                    ModelBackendFinding(
                        entry_point=ep.name,
                        value=ep.value,
                        reason=EnumBackendFindingReason.LOAD_FAILED,
                        detail=str(exc),
                    )
                )
                continue

            if not hasattr(backend_cls, "probe"):
                logger.warning(
                    "Entry point %s (%s) has no probe() classmethod — skipping",
                    ep.name,
                    ep.value,
                )
                findings.append(
                    ModelBackendFinding(
                        entry_point=ep.name,
                        value=ep.value,
                        reason=EnumBackendFindingReason.NO_PROBE,
                    )
                )
                continue

            try:
                result: ModelProbeResult = backend_cls.probe()
            except (TypeError, ValueError, AttributeError, OSError) as exc:
                logger.warning(
                    "probe() failed for entry point %s", ep.name, exc_info=True
                )
                findings.append(
                    ModelBackendFinding(
                        entry_point=ep.name,
                        value=ep.value,
                        reason=EnumBackendFindingReason.PROBE_RAISED,
                        detail=str(exc),
                    )
                )
                continue

            logger.info(
                "%s: %s (source: entry_point, package: %s, state: %s)",
                result.protocol_name,
                result.backend_name,
                result.package,
                result.state.value,
            )
            probes.setdefault(result.protocol_name, {}).setdefault(
                result.backend_name, []
            ).append((ep, backend_cls, result))

        return probes, findings
