# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract for operator-private vocabulary resolution (OMN-21494)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.private_vocabulary.model_private_vocabulary_entry import (
    ModelPrivateVocabularyEntry,
)
from omnibase_core.models.private_vocabulary.model_private_vocabulary_root import (
    ModelPrivateVocabularyRoot,
)

__all__ = ["ModelPrivateVocabularyContract"]


class ModelPrivateVocabularyContract(BaseModel):
    """Named vocabularies and the settings through which they resolve."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(description="Contract schema version.")
    workspace_config_root: ModelPrivateVocabularyRoot = Field(
        description="Workspace configuration root discovery settings."
    )
    vocabularies: tuple[ModelPrivateVocabularyEntry, ...] = Field(
        description="Declared named private vocabularies."
    )

    @model_validator(mode="after")
    def validate_unique_names(self) -> ModelPrivateVocabularyContract:
        """A vocabulary name must identify exactly one contract entry."""
        names = [entry.name for entry in self.vocabularies]
        if len(names) != len(set(names)):
            raise ValueError("vocabulary names must be unique")
        return self
