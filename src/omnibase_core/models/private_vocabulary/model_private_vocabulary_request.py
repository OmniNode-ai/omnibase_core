# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit inputs to private vocabulary resolution (OMN-21494)."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.private_vocabulary.model_private_vocabulary_file_fact import (
    ModelPrivateVocabularyFileFact,
)

__all__ = ["ModelPrivateVocabularyRequest"]


class ModelPrivateVocabularyRequest(BaseModel):
    """A vocabulary name, injected environment, reference time and file facts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    vocabulary_name: str = Field(description="Contract vocabulary name to resolve.")
    explicit_path: Path | None = Field(
        default=None, description="Explicit path override."
    )
    environment: dict[str, str] = Field(
        default_factory=dict, description="Captured declared environment values."
    )
    now: datetime = Field(description="Reference time for cache age calculation.")
    file_fact: ModelPrivateVocabularyFileFact | None = Field(
        default=None,
        description="What the read effect observed at the planned candidate path.",
    )
