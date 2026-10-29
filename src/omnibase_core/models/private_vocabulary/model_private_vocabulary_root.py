# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Declared settings for the private workspace config root (OMN-21494)."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPrivateVocabularyRoot"]


class ModelPrivateVocabularyRoot(BaseModel):
    """Environment settings and sibling used to locate private configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    env_var: str = Field(description="Environment key for the explicit config root.")
    home_env_var: str = Field(description="Environment key for the workspace home.")
    home_sibling: str = Field(description="Config directory sibling of workspace home.")
