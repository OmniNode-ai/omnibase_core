# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One input of a judgment, stored so the judgment can be replayed (OMN-22001)."""

from pydantic import BaseModel, ConfigDict, Field


class ModelJudgmentStoredInput(BaseModel):
    """An input the judge saw, kept by value.

    Attributes:
        input_ref: Reference naming the input.
        content: The input as the judge saw it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_ref: str = Field(min_length=1)
    content: str
