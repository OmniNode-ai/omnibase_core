# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import sys
import time

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

MIN_PYTHON = (3, 12)


class CheckPythonVersion(DoctorCheckBase):
    check_id = "python_version"
    check_name = "Python version"
    category = EnumDoctorCategory.ENVIRONMENT

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        current = sys.version_info[:2]
        elapsed = int((time.monotonic() - start) * 1000)
        if current >= MIN_PYTHON:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.HEALTHY,
                message=f"{current[0]}.{current[1]}",
                duration_ms=elapsed,
            )
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.UNHEALTHY,
            message=f"{current[0]}.{current[1]} (need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)",
            duration_ms=elapsed,
        )
