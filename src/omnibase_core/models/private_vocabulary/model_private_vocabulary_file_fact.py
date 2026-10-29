# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What the read effect observed at one path (OMN-21494)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPrivateVocabularyFileFact"]


class ModelPrivateVocabularyFileFact(BaseModel):
    """File facts handed to the pure resolution handler."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: Path = Field(description="Path that was inspected.")
    is_file: bool = Field(description="Whether the path is a regular file.")
    text: str | None = Field(description="File content, when it was read.")
    error: str | None = Field(
        description="One-line reason the path could not be inspected or read."
    )
