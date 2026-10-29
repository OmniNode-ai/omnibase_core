# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The path the contract's precedence order selects (OMN-21494)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_private_vocabulary_source import (
    EnumPrivateVocabularySource,
)

__all__ = ["ModelPrivateVocabularyCandidate"]


class ModelPrivateVocabularyCandidate(BaseModel):
    """One path to read, with the setting that supplied it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: Path = Field(description="Path to read.")
    source: EnumPrivateVocabularySource = Field(
        description="Setting that supplied the path."
    )
