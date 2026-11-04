# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Measurement payload; writer identity is verified by the supplying boundary."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorRuleMeasurement(BaseModel):
    """The measured replay corpus and interval, with the measurement node identity."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    corpus_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    hits: int = Field(ge=0, strict=True)
    false_matches: int = Field(ge=0, strict=True)
    interval_start: datetime
    interval_end: datetime
    written_by: str = Field(min_length=1)
