# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lander dispatch report model (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``ModelSOLanderReport``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import StrictStr, field_validator

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportLanderVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_types import (
    GitSha,
    ModelDispatchReportBase,
    PrNumber,
)
from omnibase_core.utils.util_substantive_report_text import (
    validate_substantive_report_text,
)

__all__ = ["ModelDispatchReportLander"]


class ModelDispatchReportLander(ModelDispatchReportBase):
    """Final report for the agent that merges/lands a PR."""

    role: Literal["lander"] = "lander"
    pr_number: PrNumber
    merge_sha: GitSha
    verdict: EnumDispatchReportLanderVerdict
    summary: StrictStr

    @field_validator("summary")
    @classmethod
    def _summary_is_substantive(cls, value: str) -> str:
        return validate_substantive_report_text(value, field_name="summary")
