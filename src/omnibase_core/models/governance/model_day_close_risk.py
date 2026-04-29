# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayCloseRisk — risk entry in daily close report."""

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000


class ModelDayCloseRisk(BaseModel):
    """Risk entry in daily close report."""

    model_config = ConfigDict(frozen=True)

    risk: str = Field(
        ..., description="Short risk description", max_length=_MAX_STRING_LENGTH
    )
    mitigation: str = Field(
        ..., description="Short mitigation description", max_length=_MAX_STRING_LENGTH
    )
