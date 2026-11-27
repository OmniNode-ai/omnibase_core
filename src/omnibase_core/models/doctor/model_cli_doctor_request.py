# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelCliDoctorRequest(BaseModel):
    """Which kind of install the doctor selection is for (OMN-26616)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    developer: bool = Field(
        default=False,
        description="True for a developer install, which also runs the developer-only checks",
    )
