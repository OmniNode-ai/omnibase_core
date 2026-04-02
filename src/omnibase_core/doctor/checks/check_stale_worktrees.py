# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import os
import time
from pathlib import Path

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


def _get_worktree_root() -> Path:
    return Path(
        os.environ.get("OMNI_WORKTREES", "/Volumes/PRO-G40/Code/omni_worktrees")
    )


class CheckStaleWorktrees(DoctorCheckBase):
    check_id = "stale_worktrees"
    check_name = "Stale worktrees"
    category = EnumDoctorCategory.REPOS

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        worktree_root = _get_worktree_root()
        if not worktree_root.exists():
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.HEALTHY,
                message="No worktree directory found",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        tickets = list(worktree_root.iterdir())
        count = len([t for t in tickets if t.is_dir()])
        elapsed = int((time.monotonic() - start) * 1000)
        if count > 10:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.DEGRADED,
                message=f"{count} worktree directories (consider cleanup)",
                duration_ms=elapsed,
            )
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY,
            message=f"{count} active worktrees",
            duration_ms=elapsed,
        )
