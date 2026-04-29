# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Document freshness result model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.governance.enum_doc_staleness_verdict import (
    EnumDocStalenessVerdict,
)
from omnibase_core.models.governance.model_doc_reference import ModelDocReference

_MAX_LIST_ITEMS = 10000


class ModelDocFreshnessResult(BaseModel):
    """Freshness check result for a single documentation file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_path: str = Field(..., description="Path to the .md file")
    repo: str = Field(..., description="Repository name")
    doc_last_modified: datetime = Field(
        ..., description="Last git commit that touched this file"
    )
    references: list[ModelDocReference] = Field(
        default_factory=list,
        description="All extracted references",
        max_length=_MAX_LIST_ITEMS,
    )
    broken_references: list[ModelDocReference] = Field(
        default_factory=list,
        description="References where exists == False",
        max_length=_MAX_LIST_ITEMS,
    )
    stale_references: list[ModelDocReference] = Field(
        default_factory=list,
        description="References where target was modified after doc",
        max_length=_MAX_LIST_ITEMS,
    )
    staleness_score: float = Field(
        ..., description="0.0 (fresh) to 1.0 (completely stale)", ge=0.0, le=1.0
    )
    verdict: EnumDocStalenessVerdict = Field(
        ..., description="Overall freshness verdict"
    )
    referenced_code_last_modified: datetime | None = Field(
        default=None, description="Most recent change to any referenced code"
    )

    @model_validator(mode="after")
    def validate_verdict_consistency(self) -> "ModelDocFreshnessResult":
        if (
            self.verdict == EnumDocStalenessVerdict.BROKEN
            and not self.broken_references
        ):
            msg = "Verdict is BROKEN but no broken references found"
            raise ValueError(msg)
        return self
