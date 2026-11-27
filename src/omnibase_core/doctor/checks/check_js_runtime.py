# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import importlib
import subprocess
import time

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.models.doctor.model_doctor_check_result import (
    ModelDoctorCheckResult,
)


class CheckJsRuntime(DoctorCheckBase):
    check_id = "node_version"
    check_name = "Node.js version"
    category = EnumDoctorCategory.ENVIRONMENT

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        version: str | None = None
        error: type[BaseException] | None = None
        try:
            proc = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            version = proc.stdout.strip() if proc.returncode == 0 else None
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            error = type(e)
        module = importlib.import_module(
            "omnibase_core.nodes.node_cli_doctor_effect.handler"
        )
        status, message = module.node_runtime_verdict(version, error)
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=status,
            message=message,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
