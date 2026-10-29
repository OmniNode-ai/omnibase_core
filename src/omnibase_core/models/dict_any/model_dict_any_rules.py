# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule data of the dict[str, Any] check: decorators, skipped paths, exclusion marker."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDictAnyRules"]


class ModelDictAnyRules(BaseModel):
    """Loaded from ``omnibase_core/contracts/dict_any_rules.yaml``; never code."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    allow_decorators: tuple[str, ...] = Field(min_length=1)
    skip_path_fragments: tuple[str, ...] = Field(default=())
    # Joined without a separator; kept in parts so this data file does not read as a suppression.
    exclude_marker_parts: tuple[str, ...] = Field(min_length=2)
    exclude_tag: str = Field(min_length=1)
    exclude_window_lines: int = Field(ge=0)
