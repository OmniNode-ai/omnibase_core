# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import os
import subprocess
import time

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


class CheckLinear(DoctorCheckBase):
    check_id = "linear"
    check_name = "Linear API"
    category = EnumDoctorCategory.SERVICES

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        token = os.environ.get("LINEAR_API_KEY", "")
        if not token:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNKNOWN,
                message="Skipped: LINEAR_API_KEY not set",
                duration_ms=0,
            )
        try:
            proc = subprocess.run(
                [
                    "curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}",
                    "-H", f"Authorization: {token}",
                    "https://api.linear.app/graphql",
                    "-X", "POST",
                    "-H", "Content-Type: application/json",
                    "-d", '{"query":"{ viewer { id } }"}',
                ],
                capture_output=True,
                text=True,
                timeout=10,
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
            message="Linear API reachable" if ok else "Linear API returned error",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
