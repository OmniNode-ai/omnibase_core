# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import subprocess
import time
from pathlib import Path

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

_OMNIBASE_PATH_KEY = "OMNIBASE_PATH"


def _get_omnibase_path() -> Path | None:
    """Return the multi-repo registry root from OMNIBASE_PATH, or None if unset.

    Reads through the typed bootstrap boundary (OMN-17744) rather than raw
    ``os.environ``. No default: an unset var means "skip this check" (below),
    never a silently-wrong hardcoded home-directory layout (OMN-16851).
    """
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(_OMNIBASE_PATH_KEY,)
    )
    raw = bootstrap.environment.optional(_OMNIBASE_PATH_KEY)
    return Path(raw) if raw else None


class CheckReposSynced(DoctorCheckBase):
    check_id = "repos_synced"
    check_name = "Repos synced to main"
    category = EnumDoctorCategory.REPOS

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        behind: list[str] = []
        checked = 0
        omnibase_path = _get_omnibase_path()
        if omnibase_path is None:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNKNOWN,
                message="Skipped: OMNIBASE_PATH not set",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        if not omnibase_path.exists():
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNKNOWN,
                message=f"Skipped: OMNIBASE_PATH not found ({omnibase_path})",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        for child in omnibase_path.iterdir():
            if not child.is_dir() or not (child / ".git").exists():
                continue
            checked += 1
            try:
                head = subprocess.run(
                    ["git", "-C", str(child), "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                ).stdout.strip()
                origin = subprocess.run(
                    ["git", "-C", str(child), "rev-parse", "origin/main"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                ).stdout.strip()
                if head != origin:
                    behind.append(child.name)
            except (OSError, subprocess.SubprocessError):
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
