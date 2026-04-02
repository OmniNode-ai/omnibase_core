# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import socket
import time

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


class CheckPostgres(DoctorCheckBase):
    check_id = "postgres"
    check_name = "PostgreSQL"
    category = EnumDoctorCategory.SERVICES

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        try:
            conn = socket.create_connection(("localhost", 5432), timeout=3)
            conn.close()
            ok = True
        except (OSError, socket.timeout):
            ok = False
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY if ok else EnumHealthStatusValue.UNHEALTHY,
            message="PostgreSQL accepting connections" if ok else "PostgreSQL not reachable",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
