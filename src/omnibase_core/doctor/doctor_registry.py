# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib
import threading
import time
from importlib.metadata import entry_points

from omnibase_core.models.doctor.model_doctor_check_result import (
    ModelDoctorCheckResult,
)

from .doctor_check_base import DoctorCheckBase

ENTRY_POINT_GROUP = "onex.doctor"


class DoctorRegistry:
    """Thread-safe registry for doctor checks with entry point discovery."""

    def __init__(self) -> None:
        self._checks: dict[str, type[DoctorCheckBase]] = {}
        self._lock = threading.RLock()

    def register(self, check_class: type[DoctorCheckBase]) -> None:
        with self._lock:
            cid = check_class.check_id
            if cid in self._checks:
                msg = f"Doctor check '{cid}' already registered"
                raise ValueError(msg)  # error-ok: registry duplicate guard
            self._checks[cid] = check_class

    def discover(self, developer: bool = False) -> None:
        module = importlib.import_module(
            "omnibase_core.nodes.node_doctor_registry_effect.handler"
        )
        module.discover(
            self, entry_points(group=ENTRY_POINT_GROUP), developer=developer
        )

    def list_all(self) -> list[DoctorCheckBase]:
        with self._lock:
            return [cls() for cls in self._checks.values()]

    def run_all(self) -> list[ModelDoctorCheckResult]:
        results: list[ModelDoctorCheckResult] = []
        for check in self.list_all():
            start = time.monotonic()
            try:
                result = check.run()
            except (OSError, TypeError, ValueError):
                module = importlib.import_module(
                    "omnibase_core.nodes.node_doctor_registry_effect.handler"
                )
                result = module.crashed_result(check)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            # Attach timing if not already set
            if result.duration_ms == 0:
                result = result.model_copy(update={"duration_ms": elapsed_ms})
            results.append(result)
        return results
