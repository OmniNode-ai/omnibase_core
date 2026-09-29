# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A one-shot preparation job declared by a lane's deployment."""

from pydantic import BaseModel, ConfigDict, Field


class ModelLaneOneShotJob(BaseModel):
    """A job and the declared service it prepares."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    job_name: str = Field(
        ..., min_length=1, pattern=r"\S", description="Preparation job name."
    )
    prepares_service: str = Field(
        ...,
        min_length=1,
        pattern=r"\S",
        description="Name of the declared service this job prepares.",
    )


__all__ = ["ModelLaneOneShotJob"]
