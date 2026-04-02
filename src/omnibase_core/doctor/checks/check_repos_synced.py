# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import subprocess
import time
from pathlib import Path
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

OMNI_HOME = Path("/Volumes/PRO-G40/Code/omni_home")


class CheckReposSynced(DoctorCheckBase):
    check_id = "repos_synced"
    check_name = "Repos synced to main"
    category = EnumDoctorCategory.REPOS

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        behind: list[str] = []
        checked = 0
        for child in OMNI_HOME.iterdir():
            if not child.is_dir() or not (child / ".git").exists():
                continue
            checked += 1
            try:
                head = subprocess.run(
                    ["git", "-C", str(child), "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
                origin = subprocess.run(
                    ["git", "-C", str(child), "rev-parse", "origin/main"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
                if head != origin:
                    behind.append(child.name)
            except Exception:
                behind.append(f"{child.name} (error)")

        elapsed = int((time.monotonic() - start) * 1000)
        if behind:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.DEGRADED,
                message=f"{len(behind)} repos behind: {', '.join(behind)}",
                duration_ms=elapsed,
            )
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY,
            message=f"All {checked} repos synced",
            duration_ms=elapsed,
        )
