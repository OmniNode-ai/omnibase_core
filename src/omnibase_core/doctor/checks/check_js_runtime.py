# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import subprocess
import time

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

_NOT_INSTALLED = "Node.js is not installed. Fix: Install Node.js."
_NO_ANSWER = (
    "Node.js did not answer within five seconds. Fix: Run `node --version` in a "
    "terminal and reinstall Node.js if that hangs."
)
_NOT_WORKING = (
    "Node.js is installed but running it failed. Fix: Run `node --version` in a "
    "terminal and reinstall Node.js if that hangs."
)


class CheckJsRuntime(DoctorCheckBase):
    check_id = "node_version"
    check_name = "Node.js version"
    category = EnumDoctorCategory.ENVIRONMENT

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            version = proc.stdout.strip()
            ok = proc.returncode == 0
        except FileNotFoundError:
            # A missing Node.js is reported but is not a failure (skipped): a
            # customer install does not need it to delegate or use the dashboard.
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNKNOWN,
                message=_NOT_INSTALLED,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except subprocess.TimeoutExpired:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNHEALTHY,
                message=_NO_ANSWER,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY
            if ok
            else EnumHealthStatusValue.UNHEALTHY,
            message=version if ok else _NOT_WORKING,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
