# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import subprocess
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
            proc = subprocess.run(
                ["pg_isready", "-h", "localhost", "-p", "5432"],
                capture_output=True,
                timeout=5,
            )
            ok = proc.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNHEALTHY,
                message=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY if ok else EnumHealthStatusValue.UNHEALTHY,
            message="PostgreSQL accepting connections" if ok else "PostgreSQL not reachable",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
