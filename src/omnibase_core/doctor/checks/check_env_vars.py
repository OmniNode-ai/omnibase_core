# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import os
import time
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

REQUIRED_VARS = [
    "LINEAR_API_KEY",
    "OMNICLAUDE_PROJECT_ROOT",
]


class CheckEnvVars(DoctorCheckBase):
    check_id = "env_vars"
    check_name = "Required env vars"
    category = EnumDoctorCategory.ENVIRONMENT

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        missing = [v for v in REQUIRED_VARS if not os.environ.get(v)]
        elapsed = int((time.monotonic() - start) * 1000)
        if missing:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.DEGRADED,
                message=f"Missing: {', '.join(missing)}",
                duration_ms=elapsed,
            )
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY,
            message=f"All {len(REQUIRED_VARS)} vars set",
            duration_ms=elapsed,
        )
