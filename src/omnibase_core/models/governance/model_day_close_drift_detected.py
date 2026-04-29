# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayCloseDriftDetected — drift detected entry in daily close report."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_drift_category import EnumDriftCategory

_MAX_STRING_LENGTH = 10000


class ModelDayCloseDriftDetected(BaseModel):
    """Drift detected entry in daily close report."""

    model_config = ConfigDict(frozen=True)

    drift_id: str = Field(  # string-id-ok: human-readable drift identifier slug, not a DB primary key
        ..., description="Unique drift identifier", max_length=_MAX_STRING_LENGTH
    )
    category: EnumDriftCategory = Field(..., description="Drift category")
    evidence: str = Field(
        ...,
        description="What changed / where (PRs, commits, files)",
        max_length=_MAX_STRING_LENGTH,
    )
    impact: str = Field(
        ..., description="Why it matters", max_length=_MAX_STRING_LENGTH
    )
    correction_for_tomorrow: str = Field(
        ...,
        description="Specific fix / decision / ticket",
        max_length=_MAX_STRING_LENGTH,
    )
