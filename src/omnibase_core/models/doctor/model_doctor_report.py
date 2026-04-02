# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue

from .model_doctor_check_result import ModelDoctorCheckResult

# Category display order
_CATEGORY_ORDER = [
    EnumDoctorCategory.SERVICES,
    EnumDoctorCategory.REPOS,
    EnumDoctorCategory.ENVIRONMENT,
]

_STATUS_SYMBOLS = {
    EnumHealthStatusValue.HEALTHY: "\u2713",
    EnumHealthStatusValue.DEGRADED: "~",
    EnumHealthStatusValue.UNHEALTHY: "\u2717",
    EnumHealthStatusValue.UNKNOWN: "-",
}


class ModelDoctorReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    results: list[ModelDoctorCheckResult] = Field(default_factory=list)
    total: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)

    @classmethod
    def from_results(cls, results: list[ModelDoctorCheckResult]) -> ModelDoctorReport:
        passed = sum(1 for r in results if r.is_passed())
        skipped = sum(1 for r in results if r.is_skipped())
        failed = len(results) - passed - skipped
        return cls(
            results=results,
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
        )

    def grouped(self) -> dict[EnumDoctorCategory, list[ModelDoctorCheckResult]]:
        groups: dict[EnumDoctorCategory, list[ModelDoctorCheckResult]] = defaultdict(list)
        for r in self.results:
            groups[r.category].append(r)
        return dict(groups)

    def render_human(self) -> None:
        grouped = self.grouped()
        for cat in _CATEGORY_ORDER:
            checks = grouped.get(cat, [])
            if not checks:
                continue
            cat_passed = sum(1 for c in checks if c.is_passed())
            print(f"\n{cat.value.title()} [{cat_passed}/{len(checks)} passed]")
            for c in checks:
                sym = _STATUS_SYMBOLS.get(c.status, "?")
                dur = f"({c.duration_ms / 1000:.1f}s)" if c.duration_ms > 0 else ""
                msg = f" \u2014 {c.message}" if c.message else ""
                print(f"  {sym} {c.name}{msg} {dur}")

        print(f"\nSummary: {self.passed}/{self.total} checks passed", end="")
        if self.failed:
            print(f", {self.failed} failed", end="")
        if self.skipped:
            print(f", {self.skipped} skipped", end="")
        print()

    def render_json(self) -> str:
        return json.dumps(
            {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "checks": [r.model_dump(mode="json") for r in self.results],
            },
            indent=2,
        )
