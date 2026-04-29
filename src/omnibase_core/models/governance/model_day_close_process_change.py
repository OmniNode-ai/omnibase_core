# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayCloseProcessChange — process change entry in daily close report."""

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000


class ModelDayCloseProcessChange(BaseModel):
    """Process change entry in daily close report."""

    model_config = ConfigDict(frozen=True)

    change: str = Field(
        ...,
        description="What changed in the process today",
        max_length=_MAX_STRING_LENGTH,
    )
    rationale: str = Field(
        ..., description="Why we changed it", max_length=_MAX_STRING_LENGTH
    )
    replaces: str = Field(
        ...,
        description="What it replaces / previous behavior",
        max_length=_MAX_STRING_LENGTH,
    )
