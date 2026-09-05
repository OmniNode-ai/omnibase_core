# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from importlib.metadata import entry_points

from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

from .doctor_check_base import DoctorCheckBase

ENTRY_POINT_GROUP = "onex.doctor"


class DoctorRegistry:
    """Thread-safe registry for doctor checks with entry point discovery.

    Checks are stored as *factories*, not classes (OMN-17554). Most checks
    construct with no arguments, so registering a class stores ``cls`` itself as
    the factory. A check that needs a declared dependency — ``CheckEnvVars``
    needs the user-config location it proves the binding from — registers an
    explicit factory instead.

    The factory contract is that it always returns a constructed
    ``DoctorCheckBase``. ``list_all()`` builds every check before ``run_all()``
    runs any of them, so a factory that can fail would take the whole report
    down rather than producing one unhealthy row. Whatever can fail belongs in
    ``run()``, which returns a typed result.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], DoctorCheckBase]] = {}
        self._lock = threading.RLock()

    def register(
        self,
        check_class: type[DoctorCheckBase],
        factory: Callable[[], DoctorCheckBase] | None = None,
    ) -> None:
        with self._lock:
            cid = check_class.check_id
            if cid in self._factories:
                msg = f"Doctor check '{cid}' already registered"
                raise ValueError(msg)  # error-ok: registry duplicate guard
            self._factories[cid] = factory if factory is not None else check_class

    def discover(self) -> None:
        for ep in entry_points(group=ENTRY_POINT_GROUP):
            loaded = ep.load()
            if isinstance(loaded, type) and issubclass(loaded, DoctorCheckBase):
                try:
                    self.register(loaded)
                except ValueError:
                    pass  # already registered

    def list_all(self) -> list[DoctorCheckBase]:
        with self._lock:
            return [factory() for factory in self._factories.values()]

    def run_all(self) -> list[ModelDoctorCheckResult]:
        results: list[ModelDoctorCheckResult] = []
        for check in self.list_all():
            start = time.monotonic()
            try:
                result = check.run()
            except (OSError, TypeError, ValueError) as e:
                # The exception *type* is diagnostic; its text is not safe to
                # print. A check that crashed while handling configuration can
                # carry a credential in its message (OMN-17554), and this
                # message is rendered to stdout and to the JSON report.
                result = ModelDoctorCheckResult(
                    name=check.check_name,
                    category=check.category,
                    status=EnumHealthStatusValue.UNHEALTHY,
                    message=f"Check crashed: {type(e).__name__}",
                )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            # Attach timing if not already set
            if result.duration_ms == 0:
                result = result.model_copy(update={"duration_ms": elapsed_ms})
            results.append(result)
        return results
