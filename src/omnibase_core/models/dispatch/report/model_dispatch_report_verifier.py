# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Verifier dispatch report model (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``ModelSOVerifierReport``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, StrictStr, field_validator

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportVerifierVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_types import (
    GitSha,
    ModelDispatchReportBase,
    PrNumber,
)
from omnibase_core.utils.util_substantive_report_text import (
    validate_substantive_report_text,
)

__all__ = ["ModelDispatchReportVerifier"]


class ModelDispatchReportVerifier(ModelDispatchReportBase):
    """Final report for an independent verifier re-checking an implementer's claim."""

    role: Literal["verifier"] = "verifier"
    pr_number: PrNumber
    verified_sha: GitSha
    verdict: EnumDispatchReportVerifierVerdict
    evidence_paths: list[StrictStr] = Field(min_length=1)
    summary: StrictStr

    @field_validator("summary")
    @classmethod
    def _summary_is_substantive(cls, value: str) -> str:
        return validate_substantive_report_text(value, field_name="summary")
