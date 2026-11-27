# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-bound doctor selection for customer and developer installs."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from pathlib import Path

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.models.doctor.model_cli_doctor_request import ModelCliDoctorRequest
from omnibase_core.models.doctor.model_cli_doctor_result import ModelCliDoctorResult

__all__ = [
    "DEVELOPER_ONLY",
    "NodeCliDoctorEffect",
    "builtin_checks",
    "default_builtin_checks",
    "developer_install",
]


def _check_classes() -> tuple[type[DoctorCheckBase], ...]:
    # A customer install checks what delegation, the dashboard and Claude Code
    # need. Docker, Linear, repository and worktree checks, and the check of the
    # Linear key in the user configuration, belong to a developer install.
    module = importlib.import_module("omnibase_core.doctor.checks")
    return (
        module.CheckDocker,
        module.CheckEnvVars,
        module.CheckLinear,
        module.CheckReposSynced,
        module.CheckStaleWorktrees,
    )


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

    def handle(self, request: ModelCliDoctorRequest) -> ModelCliDoctorResult:
        """Name the checks this install runs."""
        selected = self.builtin_checks(
            default_builtin_checks(), developer=request.developer
        )
        return ModelCliDoctorResult(
            check_names=tuple(check.check_name for check in selected)
        )


def builtin_checks(
    checks: Iterable[type[DoctorCheckBase]],
    developer: bool = False,
) -> list[type[DoctorCheckBase]]:
    """Keep the CLI wrapper thin by owning the selection here."""
    return NodeCliDoctorEffect().builtin_checks(checks, developer=developer)


def developer_install(omni_home: str | None = None) -> bool:
    """The same customer/developer signal for the discovery handler."""
    return NodeCliDoctorEffect.developer_install(omni_home)
