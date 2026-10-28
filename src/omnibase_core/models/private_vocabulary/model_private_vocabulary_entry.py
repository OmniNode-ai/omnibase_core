# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One named private vocabulary's resolution policy (OMN-21433)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelPrivateVocabularyEntry"]


class ModelPrivateVocabularyEntry(BaseModel):
    """Contract settings for one operator-private vocabulary."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(description="Unique vocabulary name.")
    env_var: str | None = Field(description="Optional environment path override.")
    relative_path: str = Field(description="Path under the workspace config root.")
    required: bool = Field(description="Whether an absent vocabulary is refused.")
    resolved_at_key: str | None = Field(description="Key holding the resolution time.")
    max_age_days: int | None = Field(
        ge=1, description="Optional cache age bound in days."
    )

    @model_validator(mode="after")
    def validate_age_policy(self) -> ModelPrivateVocabularyEntry:
        """An age bound requires a timestamp key."""
        if self.max_age_days is not None and self.resolved_at_key is None:
            raise ValueError("max_age_days requires resolved_at_key")
        return self
