# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lander dispatch report model (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``ModelSOLanderReport``.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import StrictStr, field_validator, model_validator

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
    merge_sha: GitSha | None = None
    verdict: EnumDispatchReportLanderVerdict
    summary: StrictStr

    @field_validator("summary")
    @classmethod
    def _summary_is_substantive(cls, value: str) -> str:
        return validate_substantive_report_text(value, field_name="summary")

    @model_validator(mode="after")
    def _merge_sha_matches_verdict(self) -> Self:
        """``merge_sha`` is a content anchor for an ACTUAL merge commit -- it
        must be present when (and only when) the verdict is ``MERGED``.
        ``BLOCKED``/``ABORTED`` land attempts happen before any merge commit
        exists, so requiring the field unconditionally would either force a
        fabricated SHA or make the field pointlessly required for the two
        verdicts where no merge ever occurred.
        """
        if (
            self.verdict == EnumDispatchReportLanderVerdict.MERGED
            and self.merge_sha is None
        ):
            raise ValueError(  # error-ok: pydantic model_validator, must raise ValueError
                "merge_sha is required when verdict is 'merged'"
            )
        if (
            self.verdict != EnumDispatchReportLanderVerdict.MERGED
            and self.merge_sha is not None
        ):
            raise ValueError(  # error-ok: pydantic model_validator, must raise ValueError
                f"merge_sha must not be set when verdict is {self.verdict.value!r} "
                "(no merge commit exists for a blocked/aborted land)"
            )
        return self
