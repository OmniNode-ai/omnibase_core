# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import os
import subprocess
import time
from pathlib import Path
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


def _get_omni_home() -> Path:
    return Path(os.environ.get("OMNI_HOME", "/Volumes/PRO-G40/Code/omni_home"))


class CheckReposSynced(DoctorCheckBase):
    check_id = "repos_synced"
    check_name = "Repos synced to main"
    category = EnumDoctorCategory.REPOS

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        behind: list[str] = []
        checked = 0
        omni_home = _get_omni_home()
        if not omni_home.exists():
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNKNOWN,
                message=f"Skipped: OMNI_HOME not found ({omni_home})",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        for child in omni_home.iterdir():
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
