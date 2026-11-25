# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-bound entry-point discovery for onex.doctor."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import Any

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase


__all__ = ["NodeDoctorRegistryEffect", "discover"]


class NodeDoctorRegistryEffect:
    """Register advertised checks under the current install's selection."""

    @staticmethod
    def _developer_only() -> frozenset[type[DoctorCheckBase]]:
        module = importlib.import_module("omnibase_core.doctor.checks")
        return frozenset(
            {module.CheckDocker, module.CheckLinear, module.CheckReposSynced}
        )

    @staticmethod
    def _developer_install() -> bool:
        module = importlib.import_module(
            "omnibase_core.nodes.node_cli_doctor_effect.handler"
        )
        return module.developer_install()

    @staticmethod
    def _base_class() -> type[DoctorCheckBase]:
        module = importlib.import_module("omnibase_core.doctor.doctor_check_base")
        return module.DoctorCheckBase

    def handle(self, request: object) -> object:
        """Runtime adapter entry point; registry uses the static seam."""
        return request

    def discover_checks(self, registry: Any, entry_points: Iterable[object]) -> None:
        """Load onex.doctor classes and keep customer installs customer-only."""
        base = self._base_class()
        exclude = frozenset() if self._developer_install() else self._developer_only()
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


def discover(registry: Any, entry_points: Iterable[object]) -> None:
    """Keep the baselined registry wrapper thin."""
    NodeDoctorRegistryEffect().discover_checks(registry, entry_points)
