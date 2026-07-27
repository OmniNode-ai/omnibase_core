# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Implementer dispatch report model (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``ModelSOImplementerReport``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, StrictStr, field_validator

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportImplementerVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_types import (
    GitSha,
    ModelDispatchReportBase,
    PrNumber,
)
from omnibase_core.utils.util_substantive_report_text import (
    validate_substantive_report_text,
)

__all__ = ["ModelDispatchReportImplementer"]


class ModelDispatchReportImplementer(ModelDispatchReportBase):
    """Final report for a build/fix agent that opened or updated a PR."""

    role: Literal["implementer"] = "implementer"
    pr_number: PrNumber
    branch: StrictStr = Field(min_length=1)
    head_sha: GitSha
    verdict: EnumDispatchReportImplementerVerdict
    files_changed_paths: list[StrictStr] = Field(min_length=1)
    summary: StrictStr

    @field_validator("summary")
    @classmethod
    def _summary_is_substantive(cls, value: str) -> str:
        return validate_substantive_report_text(value, field_name="summary")
