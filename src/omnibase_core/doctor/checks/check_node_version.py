# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import subprocess
import time
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


class CheckNodeVersion(DoctorCheckBase):
    check_id = "node_version"
    check_name = "Node.js version"
    category = EnumDoctorCategory.ENVIRONMENT

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            version = proc.stdout.strip()
            ok = proc.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNHEALTHY,
                message=f"Node.js not found: {e}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY if ok else EnumHealthStatusValue.UNHEALTHY,
            message=version if ok else "Node.js not working",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
