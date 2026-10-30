# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract parameters defining first-party tag iteration invariants."""

from pydantic import BaseModel, ConfigDict, Field


class ModelDevTagLineageInvariantPolicy(BaseModel):
    """The sibling inventory and all source/ref patterns are rule-row data."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    siblings: tuple[str, ...] = Field(min_length=1)
    normalize_pattern: str
    tag_pattern: str
    direct_git_prefix_pattern: str
    direct_git_pattern: str
    exact_pattern: str
    incompatible_source_keys: tuple[str, ...]
