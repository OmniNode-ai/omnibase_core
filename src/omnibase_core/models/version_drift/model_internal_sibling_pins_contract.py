# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The internal sibling pin contract (contracts/internal_sibling_pins.yaml, OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.version_drift.model_internal_sibling import (
    ModelInternalSibling,
)

__all__ = ["ModelInternalSiblingPinsContract"]


class ModelInternalSiblingPinsContract(BaseModel):
    """The internal siblings and the dev merge tag form a consumer must pin.

    Attributes:
        github_org: The organisation every sibling repository lives in.
        git_host: The git host every sibling repository is cloned from.
        ls_remote_timeout_seconds: Bound on one remote dev tag read.
        dev_tag_pattern: Regular expression a dev merge tag name matches.
        max_trailing_merges: Maximum dev merges a pin may trail the newest tag.
        max_trailing_hours: Maximum timestamp gap from the newest dev tag.
        siblings: The repositories that tag every dev merge.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    github_org: str = Field(min_length=1)
    git_host: str = Field(min_length=1)
    ls_remote_timeout_seconds: int = Field(gt=0, strict=True)
    dev_tag_pattern: str = Field(min_length=1)
    max_trailing_merges: int = Field(gt=0, strict=True)
    max_trailing_hours: int = Field(gt=0, strict=True)
    siblings: tuple[ModelInternalSibling, ...] = Field(min_length=1)

    def repo_url(self, repo: str) -> str:
        """The clone URL of one sibling repository."""
        return f"https://{self.git_host}/{self.github_org}/{repo}"
