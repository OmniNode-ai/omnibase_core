# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolved private vocabulary content and provenance (OMN-21433)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_private_vocabulary_source import (
    EnumPrivateVocabularySource,
)

__all__ = ["ModelPrivateVocabularyResolution"]


class ModelPrivateVocabularyResolution(BaseModel):
    """Resolution result, including optional cache age information."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    vocabulary_name: str = Field(description="Requested vocabulary name.")
    found: bool = Field(description="Whether a vocabulary file was found and read.")
    path: Path | None = Field(description="Resolved file path, when found.")
    source: EnumPrivateVocabularySource | None = Field(
        description="Setting that supplied the resolved path."
    )
    text: str | None = Field(description="Vocabulary file content, when found.")
    age_days: int | None = Field(
        description="Whole days since the resolution timestamp."
    )
    max_age_days: int | None = Field(
        description="Contract age bound, when age is known."
    )
    age_exceeded: bool = Field(description="Whether age exceeds the contract bound.")
