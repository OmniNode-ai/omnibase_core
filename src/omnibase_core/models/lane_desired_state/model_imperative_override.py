# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ModelImperativeOverride(BaseModel):
    """
    One post-apply imperative step (for example a kubectl set image) that the
    staging pipeline performs, recorded for replay.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    plane: Annotated[
        str,
        Field(..., min_length=1, description="For example 'api'."),
    ]
    resource: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            description='Key "<kind>/<name>/<container>".',
        ),
    ]
    command_summary: Annotated[
        str,
        Field(..., min_length=1, description="A summary of the imperative command."),
    ]
    replayed: Annotated[
        bool,
        Field(
            ...,
            description="True when the lane replayed this step; False is a divergence.",
        ),
    ]


__all__ = ["ModelImperativeOverride"]
