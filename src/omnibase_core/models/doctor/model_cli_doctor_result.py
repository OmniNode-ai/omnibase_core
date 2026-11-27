# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelCliDoctorResult(BaseModel):
    """The doctor checks an install runs, or the developer-only ones it leaves out."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_names: tuple[str, ...] = Field(
        default=(),
        description="Display names of the checks the selection names, in run order",
    )
