# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-bound doctor selection for customer and developer installs."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase


__all__ = [
    "DEVELOPER_ONLY",
    "NodeCliDoctorEffect",
    "builtin_checks",
    "default_builtin_checks",
    "developer_install",
]


def _check_classes() -> tuple[type[DoctorCheckBase], ...]:
    module = importlib.import_module("omnibase_core.doctor.checks")
    return (module.CheckDocker, module.CheckLinear, module.CheckReposSynced)


DEVELOPER_ONLY = frozenset(_check_classes())


def default_builtin_checks() -> list[type[DoctorCheckBase]]:
    """Return the built-in doctor check classes in registration order."""
    module = importlib.import_module("omnibase_core.doctor.checks")
    return [
        module.CheckDocker,
        module.CheckKafka,
        module.CheckPostgres,
        module.CheckLinear,
        module.CheckReposSynced,
        module.CheckStaleWorktrees,
        module.CheckEnvVars,
        module.CheckPythonVersion,
        module.CheckJsRuntime,
    ]


class NodeCliDoctorEffect:
    """Select the built-in checks and expose the install mode."""

    @staticmethod
    def developer_install(omni_home: str | None = None) -> bool:
        """OMNI_HOME that names an existing registry means developer install."""
        return bool(omni_home and Path(omni_home).is_dir())

    def builtin_checks(
        self,
        checks: Iterable[type[DoctorCheckBase]],
        developer: bool = False,
    ) -> list[type[DoctorCheckBase]]:
        """Return only the checks the current install needs."""
        selected = list(checks)
        if not developer:
            selected = [check for check in selected if check not in DEVELOPER_ONLY]
        return selected

    def handle(self, request: object) -> object:
        """Runtime adapter entry point; CLI command uses the static seams."""
        return request


def builtin_checks(
    checks: Iterable[type[DoctorCheckBase]],
    developer: bool = False,
) -> list[type[DoctorCheckBase]]:
    """Keep the CLI wrapper thin by owning the selection here."""
    return NodeCliDoctorEffect().builtin_checks(checks, developer=developer)


def developer_install(omni_home: str | None = None) -> bool:
    """The same customer/developer signal for the discovery handler."""
    return NodeCliDoctorEffect.developer_install(omni_home)
