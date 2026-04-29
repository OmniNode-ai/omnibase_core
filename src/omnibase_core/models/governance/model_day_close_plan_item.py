# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayClosePlanItem — plan item in daily close report."""

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000


class ModelDayClosePlanItem(BaseModel):
    """Plan item in daily close report."""

    model_config = ConfigDict(frozen=True)

    # string-id-ok: governance plan artifact identifier (e.g., REQ-001), not a DB primary key
    requirement_id: str = Field(
        ..., description="Requirement identifier", max_length=_MAX_STRING_LENGTH
    )
    summary: str = Field(
        ..., description="Summary of the requirement", max_length=_MAX_STRING_LENGTH
    )
