# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Scout dispatch report model (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``ModelSOScoutReport``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, StrictStr, field_validator

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportScoutVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_types import (
    ModelDispatchReportBase,
    PrNumber,
)
from omnibase_core.utils.util_substantive_report_text import (
    validate_substantive_report_text,
)

__all__ = ["ModelDispatchReportScout"]


class ModelDispatchReportScout(ModelDispatchReportBase):
    """Final report for a discovery/investigation agent (no PR required)."""

    role: Literal["scout"] = "scout"
    verdict: EnumDispatchReportScoutVerdict
    findings_paths: list[StrictStr] = Field(min_length=1)
    summary: StrictStr
    pr_number: PrNumber | None = None

    @field_validator("summary")
    @classmethod
    def _summary_is_substantive(cls, value: str) -> str:
        return validate_substantive_report_text(value, field_name="summary")
