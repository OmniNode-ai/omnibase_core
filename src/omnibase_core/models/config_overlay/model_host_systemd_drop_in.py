# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The declared content of a systemd unit drop-in."""

from pydantic import BaseModel, ConfigDict, Field


class ModelHostSystemdDropIn(BaseModel):
    """A drop-in file identified by name and content digest."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file_name: str = Field(
        ..., min_length=1, pattern=r"\S", description="Drop-in file name."
    )
    content_sha256: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="Lowercase SHA-256 digest of file content.",
    )


__all__ = ["ModelHostSystemdDropIn"]
