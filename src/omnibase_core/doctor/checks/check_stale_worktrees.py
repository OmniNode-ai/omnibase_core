# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import os
import time
from pathlib import Path

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


def _get_worktree_root() -> Path | None:
    raw = os.environ.get("OMNI_WORKTREES")
    if raw:
        return Path(raw)
    # Portable default: $HOME/omni_worktrees (or skip if not configured)
    candidate = Path.home() / "omni_worktrees"
    return candidate if candidate.exists() else None


class CheckStaleWorktrees(DoctorCheckBase):
    check_id = "stale_worktrees"
    check_name = "Stale worktrees"
    category = EnumDoctorCategory.REPOS

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        worktree_root = _get_worktree_root()
        if worktree_root is None or not worktree_root.is_dir():
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNKNOWN,
                message="Skipped: set OMNI_WORKTREES to enable this check",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        try:
            tickets = list(worktree_root.iterdir())
        except OSError:
            # Directory disappeared between is_dir() and iterdir() — race condition
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNKNOWN,
                message="Skipped: worktree directory disappeared during scan",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
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
