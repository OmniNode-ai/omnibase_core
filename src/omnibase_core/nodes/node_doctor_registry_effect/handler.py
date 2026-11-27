# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-bound entry-point discovery for onex.doctor."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from importlib.metadata import EntryPoint
from typing import Any

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_cli_doctor_request import (
    ModelCliDoctorRequest,
)
from omnibase_core.models.doctor.model_cli_doctor_result import (
    ModelCliDoctorResult,
)
from omnibase_core.models.doctor.model_doctor_check_result import (
    ModelDoctorCheckResult,
)

__all__ = ["NodeDoctorRegistryEffect", "crashed_result", "discover"]

_CRASHED = (
    "This check could not finish. Fix: Run `uv tool install --reinstall omninode-onex`."
)


def crashed_result(check: DoctorCheckBase) -> ModelDoctorCheckResult:
    """Report a check that crashed in fixed plain words, never the exception text."""
    return ModelDoctorCheckResult(
        name=check.check_name,
        category=check.category,
        status=EnumHealthStatusValue.UNHEALTHY,
        message=_CRASHED,
    )


class NodeDoctorRegistryEffect:
    """Register advertised checks under the current install's selection."""

    @staticmethod
    def _developer_only() -> frozenset[type[DoctorCheckBase]]:
        module = importlib.import_module(
            "omnibase_core.nodes.node_cli_doctor_effect.handler"
        )
        developer_only: frozenset[type[DoctorCheckBase]] = module.DEVELOPER_ONLY
        return developer_only

    @staticmethod
    def _base_class() -> type[DoctorCheckBase]:
        return DoctorCheckBase

    def handle(self, request: ModelCliDoctorRequest) -> ModelCliDoctorResult:
        """Name the developer-only checks this install leaves out."""
        excluded = frozenset() if request.developer else self._developer_only()
        return ModelCliDoctorResult(
            check_names=tuple(sorted(check.check_name for check in excluded))
        )

    def discover_checks(
        self,
        registry: Any,
        entry_points: Iterable[EntryPoint],
        developer: bool = False,
    ) -> None:
        """Load onex.doctor classes and keep customer installs customer-only."""
        base = self._base_class()
        exclude = frozenset() if developer else self._developer_only()
        registered = getattr(registry, "_checks", {})
        for entry_point in entry_points:
            loaded = entry_point.load()
            if (
                isinstance(loaded, type)
                and issubclass(loaded, base)
                and loaded not in exclude
                and loaded.check_id not in registered
            ):
                registry.register(loaded)


def discover(
    registry: Any, entry_points: Iterable[EntryPoint], developer: bool = False
) -> None:
    """Keep the baselined registry wrapper thin."""
    NodeDoctorRegistryEffect().discover_checks(
        registry, entry_points, developer=developer
    )
