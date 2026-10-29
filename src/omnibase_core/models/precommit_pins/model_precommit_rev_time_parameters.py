# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-owned effect configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPrecommitRevTimeParameters(BaseModel):
    """Contract-owned effect configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    git_timeout_seconds: float = Field(gt=0)
    cache_home_default: str = Field(min_length=1)
    cache_index_file: str = Field(min_length=1)
    cache_index_table: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    cache_repo_column: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    cache_ref_column: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    cache_path_column: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    history_repo: str
