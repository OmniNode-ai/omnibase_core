# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One reasoned machine-input path exception."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelDocumentationException(BaseModel):
    """One repository-relative machine-input path pattern and its consumer reason."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    path: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def relative_path(cls, value: str) -> str:
        if value.startswith(("/", "!")) or ".." in value.split("/") or "\\" in value:
            raise ValueError("exception paths must be repository relative")
        return value

    @field_validator("reason")
    @classmethod
    def consumer_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("exception requires a machine-consumer reason")
        return value
