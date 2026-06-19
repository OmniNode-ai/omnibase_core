# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the backend-secret-discipline COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelBackendSecretDisciplineInput(BaseModel):
    """Input payload for backend-secret-discipline COMPUTE checks."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_contents: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map of config-file relative path to raw text content. "
            "The handler checks all entries. Empty means no files checked."
        ),
    )


__all__ = ["ModelBackendSecretDisciplineInput"]
