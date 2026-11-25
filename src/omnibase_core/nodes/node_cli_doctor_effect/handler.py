# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-bound doctor selection for customer and developer installs."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from omnibase_core.doctor.doctor_check_base import DoctorCheckBase


__all__ = [
    "DEVELOPER_ONLY",
    "NodeCliDoctorEffect",
    "builtin_checks",
    "developer_install",
]


def _check_classes() -> tuple[type[DoctorCheckBase], ...]:
    module = importlib.import_module("omnibase_core.doctor.checks")
    return (module.CheckDocker, module.CheckLinear, module.CheckReposSynced)


DEVELOPER_ONLY = frozenset(_check_classes())


class NodeCliDoctorEffect:
    """Select the built-in checks and expose the install mode."""

    @staticmethod
    def developer_install() -> bool:
        """OMNI_HOME that names an existing registry means developer install."""
        raw = os.environ.get("OMNI_HOME")
        return bool(raw and Path(raw).is_dir())

    def builtin_checks(
        self, checks: Iterable[type[DoctorCheckBase]]
    ) -> list[type[DoctorCheckBase]]:
        """Return only the checks the current install needs."""
        selected = list(checks)
        if not self.developer_install():
            selected = [check for check in selected if check not in DEVELOPER_ONLY]
        return selected

    def handle(self, request: object) -> object:
        """Runtime adapter entry point; CLI command uses the static seams."""
        return request


def builtin_checks(
    checks: Iterable[type[DoctorCheckBase]],
) -> list[type[DoctorCheckBase]]:
    """Keep the CLI wrapper thin by owning the selection here."""
    return NodeCliDoctorEffect().builtin_checks(checks)


def developer_install() -> bool:
    """The same customer/developer signal for the discovery handler."""
    return NodeCliDoctorEffect.developer_install()
